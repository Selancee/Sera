"""End-to-end Sera generation pipeline."""

from __future__ import annotations

import os
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.agents.prompt_understanding_agent import PromptUnderstandingAgent
from backend.agents.revision_agent import RevisionAgent
from backend.export.midi_exporter import MidiExporter
from backend.export.musicxml_exporter import MusicXMLExporter
from backend.export.pdf_exporter import PDFExporter
from backend.generation.candidate_generator import clamp_candidate_count, generate_candidate_set
from backend.generation.rule_based_generator import GeneratedScore
from backend.generation.model_generator import ModelGenerator
from backend.generation.symbolic_generator import SymbolicMusicGenerator
from backend.models.schemas import CompositionPlan, GenerationArtifacts, ValidationResult
from backend.notation.notation_normalizer import normalize_score_document as normalize_notation_score_document
from backend.notation.notation_validator import validate_score_document_notation
from backend.storage.experiment_logger import ExperimentLogger
from backend.validation.musicxml_validator import MusicXMLValidator
from backend.validation.theory_validator import TheoryValidator
from evaluation.metrics.musicality_metrics import musicality_metrics_from_musicxml
from backend.generation.musicality.melody_line_extractor import extract_melody_lines
from backend.generation.musicality.melodic_grammar import repair_cross_measure_melody, validate_cross_measure_melody_events
from backend.services.score_consistency_service import ScoreConsistencyService
from backend.services.score_document_service import (
    build_role_coverage_report,
    infer_score_tracks,
    musicxml_to_score_document,
    score_document_to_musicxml,
    score_document_to_note_events,
)
from backend.services.key_consistency_service import KeyConsistencyService
from backend.services.score_metadata_sync_service import sync_score_metadata_after_resolution
from backend.services.score_preview_render_service import ScorePreviewRenderService
from backend.services.prompt_control_resolver import PromptControlResolver
from backend.generation.musicality.harmony_profile import build_harmony_profile
from backend.generation.musicality.melody_expectation_validator import validate_melody_expectation
from backend.generation.musicality.musicality_validator import analyze_actual_harmony_style, validate_musicality
from backend.generation.musicality.pitch_spelling import midi_to_pitch_name
from backend.generation.musicality.style_profile_mapper import map_style_profile
from backend.generation.musicality.voice_leading_validator import validate_voice_leading
from backend.generation.musicality.voicing_engine import voice_chord
from backend.generation.seed_service import create_run_seed, create_variant_id
from evaluation.analysis.music_statistics import parse_pitch_name


def _constraint_value(constraints: list[Any], key: str) -> str:
    prefix = f"{key}:"
    for constraint in constraints:
        text = str(constraint)
        if text.startswith(prefix):
            return text.split(":", 1)[1]
    return ""


class SeraPipeline:
    """Coordinate prompt agents, symbolic generation, validation, and logging."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.prompt_agent = PromptUnderstandingAgent()
        self.planning_agent = CompositionPlanningAgent()
        self.generator = self._build_generator()
        self.musicxml_validator = MusicXMLValidator()
        self.theory_validator = TheoryValidator()
        self.revision_agent = RevisionAgent()
        self.musicxml_exporter = MusicXMLExporter()
        self.midi_exporter = MidiExporter()
        self.pdf_exporter = PDFExporter()
        self.consistency_service = ScoreConsistencyService()
        self.preview_render_service = ScorePreviewRenderService(self.project_root)
        self.prompt_control_resolver = PromptControlResolver()
        self.logger = ExperimentLogger(self.project_root)
        self.model_lab = self.generator.model_generator

    def generate(
        self,
        prompt: str,
        generator_mode: str | None = None,
        musicality_controls: dict[str, Any] | None = None,
        ui_controls: dict[str, Any] | None = None,
        control_policy: dict[str, Any] | None = None,
        prompt_context: dict[str, Any] | None = None,
        ui_control_sources: dict[str, str] | None = None,
        candidate_count: int | None = None,
    ) -> dict[str, Any]:
        """Run the full generation pipeline and persist all artifacts."""

        raw_prompt = str(prompt or "").strip()
        prompt_control_resolution = self.prompt_control_resolver.resolve(raw_prompt, ui_controls or {}, control_policy or {}, ui_control_sources or {})
        intent = self.prompt_agent.understand(raw_prompt)
        self._attach_prompt_diagnostics(intent, prompt_control_resolution, prompt_context or {})
        self._apply_resolved_controls(intent, prompt_control_resolution.get("resolved_controls", {}))
        if musicality_controls:
            self._apply_musicality_controls(intent, musicality_controls)
        candidate_count = clamp_candidate_count(candidate_count or (musicality_controls or {}).get("candidate_count"))
        self._ensure_run_seed(intent, raw_prompt, musicality_controls or {})
        plan = self.planning_agent.plan(intent)
        return self._persist_generated_plan(prompt=raw_prompt, plan=plan, generator_mode=generator_mode, candidate_count=candidate_count)

    def revise(self, run_id: str, feedback: str) -> dict[str, Any]:
        """Revise an existing run using feedback and persist a new run."""

        previous = self.logger.get_record(run_id)
        if previous is None:
            raise KeyError(f"Unknown run_id: {run_id}")
        previous_plan = CompositionPlan.from_dict(previous["plan"])
        previous_validation = ValidationResult(
            valid=bool(previous.get("validation", {}).get("valid", False)),
            issues=list(previous.get("validation", {}).get("issues", [])),
            warnings=list(previous.get("validation", {}).get("warnings", [])),
            metrics=dict(previous.get("validation", {}).get("metrics", {})),
        )
        revised_plan, revision = self.revision_agent.revise(previous_plan, previous_validation, feedback)
        prompt = previous["prompt"] + f"\nRevision feedback: {feedback}"
        revised_plan.intent.prompt = prompt
        return self._persist_generated_plan(
            prompt=prompt,
            plan=revised_plan,
            revision=revision,
            previous_record=previous,
        )

    def evaluate_run(self, run_id: str) -> dict[str, Any]:
        """Return evaluation metrics for a persisted run."""

        record = self.logger.get_record(run_id)
        if record is None:
            raise KeyError(f"Unknown run_id: {run_id}")
        return record.get("evaluation", {})

    def symbolic_model_status(self) -> dict[str, Any]:
        """Return status for the optional trained symbolic model."""

        status = self.model_lab.status()
        status["generator_backend"] = self.generator.backend
        return status

    def symbolic_model_registry(self) -> dict[str, Any]:
        """Return local symbolic models that can be selected at runtime."""

        registry = self.model_lab.model_registry()
        registry["generator_backend"] = self.generator.backend
        return registry

    def select_symbolic_model(self, model_name: str, persist: bool = False) -> dict[str, Any]:
        """Switch the active symbolic model for subsequent generation calls."""

        selection = self.model_lab.set_active_model(model_name)
        os.environ["SERA_GENERATOR_BACKEND"] = "model"
        env_path = ""
        if persist:
            env_path = str(self._persist_model_environment(selection["active_model"], selection["expected_model_dir"]))
        self.generator = self._build_generator()
        self.model_lab = self.generator.model_generator
        status = self.symbolic_model_status()
        status["selection_persisted"] = persist
        status["env_path"] = env_path
        return status

    def symbolic_model_sample(self, prompt: str, max_tokens: int = 96) -> dict[str, Any]:
        """Generate or replay a qualitative symbolic-model token sample."""

        payload = self.model_lab.sample_tokens(prompt, max_tokens=max_tokens)
        if isinstance(payload.get("status"), dict):
            payload["status"]["generator_backend"] = self.generator.backend
        return payload

    def _build_generator(self, backend: str | None = None) -> SymbolicMusicGenerator:
        """Create the configured symbolic generator facade."""

        generator_backend = backend or os.getenv("SERA_GENERATOR_BACKEND", "rule_based").strip() or "rule_based"
        return SymbolicMusicGenerator(backend=generator_backend, project_root=self.project_root)

    @staticmethod
    def _attach_prompt_diagnostics(intent: Any, resolution: dict[str, Any], prompt_context: dict[str, Any]) -> None:
        intent.raw_prompt = str(resolution.get("raw_prompt") or intent.prompt)
        intent.ui_controls = dict(resolution.get("ui_controls") or {})
        intent.prompt_terms = list(resolution.get("prompt_terms") or intent.prompt_terms)
        intent.source_prompt_terms = list(resolution.get("source_prompt_terms") or intent.source_prompt_terms)
        intent.unparsed_prompt_terms = list(resolution.get("unparsed_prompt_terms") or intent.unparsed_prompt_terms)
        intent.prompt_ui_conflicts = list(resolution.get("conflicts") or [])
        intent.intent_source = str(resolution.get("intent_source") or "raw_prompt")
        intent.source_control_terms = list(resolution.get("source_control_terms") or [])
        intent.control_only_intent = bool(resolution.get("control_only_intent", False))
        intent.resolved_generation_request = {
            "raw_prompt": intent.raw_prompt,
            "ui_controls": intent.ui_controls,
            "resolved_controls": dict(resolution.get("resolved_controls") or {}),
            "intent_source": intent.intent_source,
            "source_control_terms": list(intent.source_control_terms),
            "control_only_intent": bool(intent.control_only_intent),
            "defaults_used": list(resolution.get("defaults_used") or []),
            "prompt_context": dict(prompt_context or {}),
            "warnings": list(resolution.get("warnings") or []),
        }

    @staticmethod
    def _apply_resolved_controls(intent: Any, controls: dict[str, Any]) -> None:
        if not controls:
            return
        defaults_used = set((intent.resolved_generation_request or {}).get("defaults_used", []))
        if controls.get("style"):
            style = str(controls["style"])
            if style in {"cyberpunk", "anime", "game", "cinematic", "new_age"}:
                mapped = map_style_profile(style, style)
                intent.style = str(mapped.get("style") or ("custom" if style == "cyberpunk" else style))
                intent.base_style = str(mapped.get("base_style") or ("electronic" if style == "cyberpunk" else style))
                intent.custom_style_tags = list(mapped.get("custom_style_tags") or [style])
                intent.style_profile = {**dict(intent.style_profile or {}), **dict(mapped.get("style_profile") or {})}
            else:
                intent.style = style
                intent.base_style = style
        if controls.get("key"):
            intent.key = str(controls["key"])
        if controls.get("meter"):
            intent.time_signature = str(controls["meter"])
        if controls.get("length_measures"):
            try:
                intent.bars = int(controls["length_measures"])
            except (TypeError, ValueError):
                pass
        if controls.get("tempo"):
            try:
                intent.tempo_bpm = int(controls["tempo"])
            except (TypeError, ValueError):
                pass
        if controls.get("instrumentation"):
            intent.instruments = [str(controls["instrumentation"])]
        for source, target in {
            "rhythmic_density": "rhythmic_density",
            "difficulty": "difficulty",
            "texture": "texture",
            "syncopation": "syncopation",
        }.items():
            value = controls.get(source)
            if isinstance(value, str) and value:
                if source in defaults_used and intent.style_profile.get(source):
                    continue
                if target == "syncopation":
                    intent.style_profile.setdefault("syncopation", value)
                else:
                    setattr(intent, target, value)
                    intent.constraints.append(f"{source}:{value}")
        if controls.get("accompaniment_style"):
            intent.constraints.append(f"accompaniment_style:{controls['accompaniment_style']}")
            intent.style_profile.setdefault("accompaniment_style", controls["accompaniment_style"])
        if controls.get("cadence_strength"):
            intent.constraints.append(f"cadence_strength:{controls['cadence_strength']}")
            intent.style_profile.setdefault("cadence_strength", controls["cadence_strength"])

    @staticmethod
    def _apply_musicality_controls(intent: Any, controls: dict[str, Any]) -> None:
        for source, target in {
            "rhythmic_density": "rhythmic_density",
            "difficulty": "difficulty",
            "texture": "texture",
            "cadence_strength": "cadence",
        }.items():
            value = controls.get(source)
            if isinstance(value, str) and value:
                setattr(intent, target, "authentic" if source == "cadence_strength" and value in {"clear", "strong"} else value)
                intent.constraints.append(f"{source}:{value}")
        accompaniment = controls.get("accompaniment_style")
        if accompaniment:
            intent.constraints.append(f"accompaniment_style:{accompaniment}")
        variation_seed = controls.get("variation_seed")
        if isinstance(variation_seed, str) and variation_seed.strip():
            intent.constraints.append(f"variation_seed:{variation_seed.strip()[:120]}")
        variation_index = controls.get("variation_index")
        if variation_index is not None:
            try:
                intent.constraints.append(f"variation_index:{int(variation_index)}")
            except (TypeError, ValueError):
                pass

    @staticmethod
    def _ensure_run_seed(intent: Any, raw_prompt: str, controls: dict[str, Any]) -> None:
        existing_seed = _constraint_value(intent.constraints, "run_seed")
        existing_variation = _constraint_value(intent.constraints, "variation_seed")
        explicit = controls.get("run_seed") or existing_seed or controls.get("variation_seed") or existing_variation
        seed_controls = dict(controls or {})
        if explicit not in {None, ""}:
            seed_controls["run_seed"] = explicit
        run_seed = int(existing_seed or create_run_seed(raw_prompt, seed_controls))
        seed_source = "user" if explicit not in {None, ""} else "backend_auto"
        intent.run_seed = run_seed
        intent.seed_source = seed_source
        intent.variant_id = str(controls.get("variant_id") or create_variant_id(run_seed))
        intent.generation_nonce = str(controls.get("generation_nonce") or uuid.uuid4().hex)
        if not existing_seed:
            intent.constraints.append(f"run_seed:{run_seed}")
        if not existing_variation:
            intent.constraints.append(f"variation_seed:{run_seed}")
        intent.constraints.append(f"seed_source:{seed_source}")
        intent.constraints.append(f"variant_id:{intent.variant_id}")
        intent.resolved_generation_request = dict(intent.resolved_generation_request or {})
        intent.resolved_generation_request.update(
            {
                "run_seed": run_seed,
                "seed_source": seed_source,
                "variant_id": intent.variant_id,
                "generation_nonce": intent.generation_nonce,
            }
        )

    def _persist_model_environment(self, model_name: str, model_dir: str) -> Path:
        """Persist the active model without touching API keys or user secrets."""

        env_path = self.project_root / ".env"
        model_env = {
            "SERA_ACTIVE_SYMBOLIC_MODEL": model_name,
            "SERA_SYMBOLIC_MODEL_DIR": model_dir,
            "SERA_SYMBOLIC_MODEL_CHECKPOINT": "",
            "SERA_GENERATOR_BACKEND": "model",
        }
        existing = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        filtered = [
            line
            for line in existing
            if not any(line.startswith(f"{key}=") for key in model_env)
        ]
        if filtered and filtered[-1].strip():
            filtered.append("")
        filtered.extend(f"{key}={value}" for key, value in model_env.items())
        env_path.write_text("\n".join(filtered) + "\n", encoding="utf-8")
        return env_path

    def rate_run(self, run_id: str, rating: dict[str, Any]) -> dict[str, Any]:
        """Persist a human evaluation rating for one generated run."""

        record = self.logger.get_record(run_id)
        if record is None:
            raise KeyError(f"Unknown run_id: {run_id}")

        normalized = self._normalize_rating(rating)
        experiment_dir = Path(record.get("artifacts", {}).get("experiment_dir") or self.logger.experiment_dir(run_id))
        rating_path = experiment_dir / "human_rating.json"
        self.logger.write_json(rating_path, normalized)

        updated = dict(record)
        updated["user_rating"] = normalized
        updated.setdefault("metadata", {})["human_rating_path"] = str(rating_path)
        updated.setdefault("metadata", {})["human_rating_average"] = normalized["average_score"]
        updated.setdefault("artifacts", {}).setdefault("export_files", [])
        if str(rating_path) not in updated["artifacts"]["export_files"]:
            updated["artifacts"]["export_files"].append(str(rating_path))
        self.logger.write_json(experiment_dir / "experiment_log.json", updated)
        self.logger.append(updated)
        return updated

    def evaluate_payload(
        self,
        plan: CompositionPlan,
        validation: ValidationResult,
        revision: dict[str, Any],
        musicxml: str = "",
        generation_seconds: float = 0.0,
    ) -> dict[str, Any]:
        """Compute paper-facing metrics for one generated score."""

        structural = self.theory_validator.validate_plan(plan)
        measure_count = max(1, int(validation.metrics.get("measure_count", len(plan.measures))))
        empty_rate = int(validation.metrics.get("empty_measure_count", 0)) / measure_count
        valid_musicxml = 1.0 if validation.metrics.get("valid_musicxml") else 0.0
        midi_success = 1.0 if validation.metrics.get("midi_export_success") else 0.0
        pdf_success = 1.0 if validation.metrics.get("pdf_export_success") else 0.0
        pitch_success = 1.0 if validation.metrics.get("pitch_range_valid") else 0.0
        prompt_score = structural.metrics.get("prompt_adherence_proxy", 0.0)
        revision_success = 1.0 if validation.valid else 0.0
        musicality = musicality_metrics_from_musicxml(musicxml) if musicxml else {}
        return {
            "musicxml_validity_rate": valid_musicxml,
            "midi_export_success_rate": midi_success,
            "pdf_export_success_rate": pdf_success,
            "bar_completeness_score": validation.metrics.get("bar_completeness_score", 0.0),
            "pitch_range_validity_rate": pitch_success,
            "empty_measure_rate": empty_rate,
            "prompt_adherence_rule_score": prompt_score,
            "revision_success_rate": revision_success,
            # Backward-compatible MVP metric names used by old tests/UI.
            "musicxml_validity": valid_musicxml,
            "bar_completeness": validation.metrics.get("bar_completeness_score", 0.0),
            "pitch_range_validity": pitch_success,
            "prompt_adherence": prompt_score,
            "structural_consistency": structural.metrics.get("structural_consistency", 0.0),
            "revision_changes": revision.get("changes", []),
            "baseline": plan.baseline,
            "average_generation_time": round(float(generation_seconds), 4),
            **musicality,
        }

    def artifact_path(self, run_id: str, file_format: str) -> Path:
        """Return a generated artifact path for a run and format."""

        experiment = self.logger.experiments_dir / run_id
        mapping = {
            "musicxml": self.project_root / "examples" / "scores" / f"{run_id}.musicxml",
            "midi": self.project_root / "examples" / "midi" / f"{run_id}.mid",
            "abc": self.project_root / "examples" / "abc" / f"{run_id}.abc",
            "pdf": self.project_root / "examples" / "pdf" / f"{run_id}.pdf",
            "plan": experiment / "plan.json",
            "json_plan": experiment / "plan.json",
            "validation_report": experiment / "validation_report.json",
            "experiment_log": experiment / "experiment_log.json",
            "metadata": experiment / "metadata.json",
        }
        if file_format not in mapping:
            raise KeyError(f"Unsupported export format: {file_format}")
        return mapping[file_format]

    def _persist_generated_plan(
        self,
        prompt: str,
        plan: CompositionPlan,
        revision: dict[str, Any] | None = None,
        previous_record: dict[str, Any] | None = None,
        generator_mode: str | None = None,
        candidate_count: int = 4,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        runtime_generator = self._build_generator(generator_mode) if generator_mode else self.generator
        candidate_bundle = generate_candidate_set(
            plan,
            generate_one=lambda candidate_plan: self._canonicalize_generated_score(
                prompt,
                runtime_generator.generate(candidate_plan),
                candidate_plan.intent,
            ),
            validate_one=lambda candidate_plan, candidate_generated: self._combined_validation(candidate_plan, candidate_generated.musicxml),
            candidate_count=candidate_count,
        )
        selected_candidate = candidate_bundle["selected"]
        plan = selected_candidate["plan"]
        generated = selected_candidate["generated"]
        preliminary = selected_candidate["validation"]
        generated.metadata = dict(generated.metadata or {})
        generated.metadata["candidate_generation"] = candidate_bundle["candidate_generation"]
        generated.metadata["candidate_rank_report"] = selected_candidate["rank_report"]
        revision = revision or {
            "agent": "revision_agent_v0_2",
            "feedback": "",
            "changes": ["no structural repair required"],
            "valid_before_revision": preliminary.valid,
        }

        if not preliminary.valid and previous_record is None:
            repaired_plan, revision = self.revision_agent.revise(plan, preliminary)
            plan = repaired_plan
            generated = self._canonicalize_generated_score(prompt, runtime_generator.generate(plan), plan.intent)
            generated.metadata = dict(generated.metadata or {})
            generated.metadata["candidate_generation"] = candidate_bundle["candidate_generation"]
            generated.metadata["candidate_rank_report"] = selected_candidate["rank_report"]
            preliminary = self._combined_validation(plan, generated.musicxml)

        run_id = self.logger.new_run_id(prompt)
        artifacts = self._write_artifacts(run_id, plan, generated)
        preview_render = self.preview_render_service.render_musicxml(generated.musicxml, output_format="svg", render_id=run_id)
        generated.metadata = dict(generated.metadata or {})
        generated.metadata["preview_render"] = preview_render
        if preview_render.get("svg_url"):
            generated.metadata["backend_rendered_svg_url"] = preview_render["svg_url"]
        prompt_path = Path(artifacts.experiment_dir) / "prompt.txt"
        self.logger.write_text(prompt_path, prompt)
        artifacts.export_files.append(str(prompt_path))
        validation = self._combined_validation(plan, generated.musicxml, artifacts)
        generation_seconds = time.perf_counter() - started
        generated.metadata = dict(generated.metadata or {})
        generated.metadata["final_validation_report"] = validation.to_report()
        evaluation = self.evaluate_payload(plan, validation, revision, generated.musicxml, generation_seconds)

        self.logger.write_json(artifacts.validation_report_path, validation.to_report())
        metadata = self._metadata(prompt, plan, artifacts, validation, revision, generated)
        self.logger.write_json(artifacts.metadata_path, metadata)
        self.logger.write_json(
            artifacts.revision_history_path,
            self._revision_history(previous_record, plan, revision, preliminary),
        )

        record = self._record(run_id, prompt, plan, artifacts, validation, revision, evaluation, metadata, generated)
        self.logger.write_json(artifacts.experiment_log_path, record)
        self.logger.append(record)
        return record | {
            "musicxml": generated.musicxml,
            "abc": generated.abc,
            "midi_url": record.get("midi_url", ""),
            "exports": record.get("exports", {}),
            "generation_metadata": generated.metadata or {},
            "consistency_report": record.get("consistency_report", {}),
            "key_consistency_report": record.get("key_consistency_report", {}),
            "preview_render": record.get("preview_render", {}),
            "backend_rendered_svg_url": record.get("backend_rendered_svg_url", ""),
            "backend_rendered_png_url": record.get("backend_rendered_png_url", ""),
        }

    @staticmethod
    def _canonicalize_generated_score(prompt: str, generated: GeneratedScore, intent: Any | None = None) -> GeneratedScore:
        """Make ScoreDocument the source for final MusicXML and MIDI events."""

        metadata = dict(generated.metadata or {})
        try:
            score_document = musicxml_to_score_document(generated.musicxml, prompt=prompt, source="generated")
            score_document.setdefault("metadata", {})["generation_metadata"] = dict(metadata)
            score_document.setdefault("metadata", {})["v09_profile"] = dict(metadata.get("generation_profile", {}))
            profile_seed = dict(metadata.get("generation_profile", {}) or {})
            score_document["metadata"]["run_seed"] = profile_seed.get("run_seed", 0)
            score_document["metadata"]["seed_source"] = profile_seed.get("seed_source", "")
            score_document["metadata"]["variant_id"] = profile_seed.get("variant_id", "")
            SeraPipeline._apply_generation_metadata_to_score_document(score_document, metadata)
            notation_result = normalize_notation_score_document(score_document)
            score_document = notation_result.score_document
            notation_validation = validate_score_document_notation(score_document)
            intent_dict = intent.to_dict() if hasattr(intent, "to_dict") else dict(intent or {})
            resolved_controls = dict((getattr(intent, "resolved_generation_request", {}) or {}).get("resolved_controls", {}) or {})
            sync_result = sync_score_metadata_after_resolution(
                intent=intent_dict,
                resolved_controls=resolved_controls,
                score_document=score_document,
            )
            score_document = sync_result["score_document"]
            synced_intent = sync_result["intent"]
            if intent is not None:
                if hasattr(intent, "title"):
                    intent.title = str(synced_intent.get("title") or getattr(intent, "title", ""))
                if hasattr(intent, "key"):
                    intent.key = str(synced_intent.get("key") or getattr(intent, "key", ""))
            style_profile = dict(metadata.get("melodic_style_profile") or metadata.get("generation_profile", {}).get("style_profile") or {})
            difficulty = str(metadata.get("generation_profile", {}).get("difficulty") or getattr(intent, "difficulty", "intermediate"))
            key = str(score_document.get("global", {}).get("key") or synced_intent.get("key") or "C major")
            mode = "minor" if "minor" in key.lower() else "major"
            generation_profile = dict(metadata.get("generation_profile") or {})
            style_profile.setdefault("style", generation_profile.get("style") or synced_intent.get("style") or "classical")
            style_profile.setdefault("base_style", generation_profile.get("base_style") or synced_intent.get("base_style") or style_profile.get("style", "classical"))
            style_profile.setdefault("custom_style_tags", generation_profile.get("custom_style_tags") or synced_intent.get("custom_style_tags") or [])
            style_profile.setdefault("key", key)
            melody_line_report = extract_melody_lines(score_document)
            primary_events = list(melody_line_report.get("primary_melody", {}).get("events", []))
            cross_measure_report = validate_cross_measure_melody_events(primary_events, key, mode, style_profile, difficulty)
            if not cross_measure_report.get("valid", True):
                score_document, repair_report = repair_cross_measure_melody(score_document, primary_events, key, mode, style_profile, difficulty)
                melody_line_report = extract_melody_lines(score_document)
                primary_events = list(melody_line_report.get("primary_melody", {}).get("events", []))
                cross_measure_report = validate_cross_measure_melody_events(primary_events, key, mode, style_profile, difficulty)
                cross_measure_report["repairs_applied"] = repair_report.get("repairs_applied", [])
            final_harmony_alignment_report = SeraPipeline._repair_final_score_harmony_alignment(score_document, metadata, key, mode)
            if final_harmony_alignment_report.get("repair_count"):
                melody_line_report = extract_melody_lines(score_document)
                primary_events = list(melody_line_report.get("primary_melody", {}).get("events", []))
                cross_measure_report = validate_cross_measure_melody_events(primary_events, key, mode, style_profile, difficulty)
            melody_expectation_report = validate_melody_expectation(
                primary_events,
                harmony_context=list((metadata.get("harmony_plan") or {}).get("chords", [])),
                key=key,
                style_profile=style_profile,
            )
            harmony_profile = build_harmony_profile(style_profile, key=key, mode=mode, difficulty=difficulty)
            harmony_metadata = dict(metadata.get("harmony_plan") or {})
            chords = list(harmony_metadata.get("chords") or harmony_metadata.get("progression") or getattr(intent, "harmony_plan", []) or [])
            voicing_reports = []
            previous_voicing: list[int] | None = None
            for chord in chords[: max(1, len(score_document.get("measures", [])))]:
                voicing = voice_chord(str(chord), harmony_profile, register="left_hand", role="accompaniment", previous_voicing=previous_voicing)
                previous_voicing = list(voicing.get("voicing", []))
                voicing_reports.append(voicing)
            voice_leading_report = validate_voice_leading(voicing_reports, harmony_profile)
            score_document["tracks"] = infer_score_tracks(score_document)
            role_coverage_report = build_role_coverage_report(score_document)
            musicality_validation = validate_musicality(score_document, metadata)
            actual_harmony_style_report = analyze_actual_harmony_style(score_document, metadata)
            canonical_musicxml = score_document_to_musicxml(score_document)
            note_events = score_document_to_note_events(score_document)
            metadata["authoritative_score_source"] = "score_document"
            metadata["score_document_event_count"] = sum(len(measure.get("events", [])) for measure in score_document.get("measures", []))
            metadata["metadata_sync_report"] = sync_result["metadata_sync_report"]
            metadata["key_consistency_report"] = KeyConsistencyService().build_report(
                intent=synced_intent,
                resolved_controls=resolved_controls,
                score_document=score_document,
                musicxml=canonical_musicxml,
                metadata_sync_report=sync_result["metadata_sync_report"],
            )
            metadata["melody_line_report"] = melody_line_report
            metadata["cross_measure_melodic_grammar_report"] = cross_measure_report
            metadata["melody_expectation_report"] = melody_expectation_report
            metadata["melody_expectation_score"] = melody_expectation_report.get("melody_expectation_score", 0.0)
            metadata["harmony_profile"] = harmony_profile
            metadata["progression_source"] = harmony_metadata.get("progression_source") or f"{harmony_profile.get('style', 'classical')}_harmony_profile"
            metadata["voicing_report"] = {
                "engine": "voicing_engine_v096",
                "voicings": voicing_reports,
            }
            metadata["voice_leading_report"] = voice_leading_report
            metadata["final_score_harmony_alignment_report"] = final_harmony_alignment_report
            metadata["actual_harmony_style_report"] = actual_harmony_style_report
            metadata["harmony_style_score"] = min(
                float(voice_leading_report.get("style_harmony_match_score", 0.0) or 0.0),
                float(actual_harmony_style_report.get("style_harmony_match_score", 0.0) or 0.0),
            )
            metadata["track_plan"] = list(score_document.get("tracks", []))
            metadata["role_coverage_report"] = role_coverage_report
            metadata["prompt_plan_alignment_score"] = float(getattr(intent, "prompt_plan_alignment_score", 0.0) or 0.0)
            metadata["notation_normalization_report"] = {
                "changed": notation_result.changed,
                "operations": notation_result.operations,
                "warnings": notation_result.warnings,
                "errors": notation_result.errors,
                "report": notation_result.report,
            }
            metadata["notation_validation_report"] = notation_validation
            metadata["musicality_validation_report"] = musicality_validation
            score_document.setdefault("metadata", {})["generation_metadata"] = dict(metadata)
            return GeneratedScore(
                musicxml=canonical_musicxml,
                abc=generated.abc,
                note_events=note_events,
                metadata=metadata,
                score_document=score_document,
            )
        except Exception as exc:  # noqa: BLE001 - keep generation fallback-safe.
            metadata.setdefault("warnings", []).append(f"ScoreDocument canonicalization fallback: {exc}")
            return GeneratedScore(
                musicxml=generated.musicxml,
                abc=generated.abc,
                note_events=generated.note_events,
                metadata=metadata,
                score_document={},
            )

    @staticmethod
    def _repair_final_score_harmony_alignment(
        score_document: dict[str, Any],
        metadata: dict[str, Any],
        key: str,
        mode: str,
    ) -> dict[str, Any]:
        repairs: list[dict[str, Any]] = []
        tonic_pc = SeraPipeline._key_tonic_pc(key)
        chords = list((metadata.get("harmony_plan") or {}).get("chords") or [])
        for measure in score_document.get("measures", []):
            measure_number = int(measure.get("number", 1) or 1)
            chord = str(chords[measure_number - 1]) if measure_number - 1 < len(chords) else str(measure.get("harmony") or "")
            clean = SeraPipeline._clean_roman_symbol(chord)
            repairs.extend(SeraPipeline._remove_final_duplicate_note_events(measure))
            left_events = [event for event in measure.get("events", []) if event.get("staff") == "left_hand" and event.get("type") != "rest"]
            right_events = [event for event in measure.get("events", []) if event.get("staff") != "left_hand" and event.get("type") != "rest"]
            if mode == "minor":
                repairs.extend(SeraPipeline._repair_final_minor_left_hand_quality(left_events, clean, tonic_pc, key, measure_number))
            if mode == "minor" and (clean in {"V", "V7"} or clean.startswith("V/")):
                natural_seventh = (tonic_pc + 10) % 12
                raised_leading = (tonic_pc + 11) % 12
                for event in right_events:
                    midi = parse_pitch_name(str(event.get("pitch", "")))
                    if midi is None or midi % 12 != natural_seventh:
                        continue
                    replacement = SeraPipeline._nearest_pitch_class_in_register(midi, raised_leading)
                    before = str(event.get("pitch", ""))
                    event["pitch"] = midi_to_pitch_name(replacement, key, mode)
                    repairs.append(
                        {
                            "measure": measure_number,
                            "event_id": str(event.get("event_id", "")),
                            "from": before,
                            "to": event["pitch"],
                            "reason": "final_minor_dominant_raised_leading_tone",
                        }
                    )
            repairs.extend(SeraPipeline._repair_final_measure_accidental_consistency(measure, key, mode, measure_number))
            repairs.extend(SeraPipeline._repair_final_augmented_unison_octaves(measure, key, mode))
            repairs.extend(SeraPipeline._remove_final_duplicate_note_events(measure))
        return {
            "engine": "final_score_harmony_alignment_v0962",
            "repair_count": len(repairs),
            "repairs": repairs,
        }

    @staticmethod
    def _remove_final_duplicate_note_events(measure: dict[str, Any]) -> list[dict[str, Any]]:
        seen: set[tuple[str, int, float, str, str]] = set()
        kept: list[dict[str, Any]] = []
        repairs: list[dict[str, Any]] = []
        for event in measure.get("events", []):
            if event.get("type") == "rest":
                kept.append(event)
                continue
            key = (
                str(event.get("staff", "right_hand")),
                int(event.get("voice", 1) or 1),
                round(float(event.get("offset", 0.0) or 0.0), 4),
                str(event.get("duration", "quarter")),
                str(event.get("pitch", "")),
            )
            if key in seen:
                repairs.append(
                    {
                        "measure": int(measure.get("number", 1) or 1),
                        "event_id": str(event.get("event_id", "")),
                        "pitch": str(event.get("pitch", "")),
                        "reason": "final_duplicate_note_event_removed",
                    }
                )
                continue
            seen.add(key)
            kept.append(event)
        if len(kept) != len(measure.get("events", [])):
            measure["events"] = kept
        return repairs

    @staticmethod
    def _repair_final_minor_left_hand_quality(
        left_events: list[dict[str, Any]],
        clean_chord: str,
        tonic_pc: int,
        key: str,
        measure_number: int,
    ) -> list[dict[str, Any]]:
        pc_rewrites: dict[int, int] = {}
        if clean_chord in {"I", "i"}:
            pc_rewrites[(tonic_pc + 4) % 12] = (tonic_pc + 3) % 12
        elif clean_chord in {"IV", "iv"}:
            pc_rewrites[(tonic_pc + 9) % 12] = (tonic_pc + 8) % 12
        elif clean_chord == "ii":
            pc_rewrites[(tonic_pc + 9) % 12] = (tonic_pc + 8) % 12
        repairs: list[dict[str, Any]] = []
        if not pc_rewrites:
            return repairs
        for event in left_events:
            midi = parse_pitch_name(str(event.get("pitch", "")))
            if midi is None:
                continue
            target_pc = pc_rewrites.get(midi % 12)
            if target_pc is None:
                continue
            replacement = SeraPipeline._nearest_pitch_class_in_register(midi, target_pc)
            before = str(event.get("pitch", ""))
            event["pitch"] = midi_to_pitch_name(replacement, key)
            repairs.append(
                {
                    "measure": measure_number,
                    "event_id": str(event.get("event_id", "")),
                    "from": before,
                    "to": event["pitch"],
                    "reason": "final_minor_left_hand_chord_quality_alignment",
                }
            )
        return repairs

    @staticmethod
    def _repair_final_measure_accidental_consistency(
        measure: dict[str, Any],
        key: str,
        mode: str,
        measure_number: int,
    ) -> list[dict[str, Any]]:
        del key, mode
        grouped: dict[str, list[dict[str, Any]]] = {}
        for event in measure.get("events", []):
            if event.get("type") == "rest":
                continue
            parsed = SeraPipeline._parse_pitch_token(str(event.get("pitch", "")))
            if not parsed:
                continue
            grouped.setdefault(parsed["step"], []).append({**parsed, "event": event})

        repairs: list[dict[str, Any]] = []
        for step, items in grouped.items():
            accidentals = {str(item["accidental"]) for item in items}
            if len(accidentals) <= 1:
                continue
            staves = {str(item["event"].get("staff", "right_hand")) for item in items}
            if len(staves) <= 1:
                continue
            preferred = SeraPipeline._preferred_measure_accidental(items)
            for item in items:
                if item["accidental"] == preferred:
                    continue
                event = item["event"]
                before = str(event.get("pitch", ""))
                event["pitch"] = SeraPipeline._spell_fixed_step_pitch(step, preferred, int(item["octave"]))
                repairs.append(
                    {
                        "measure": measure_number,
                        "event_id": str(event.get("event_id", "")),
                        "from": before,
                        "to": event["pitch"],
                        "reason": "final_measure_accidental_consistency",
                    }
                )
        return repairs

    @staticmethod
    def _preferred_measure_accidental(items: list[dict[str, Any]]) -> str:
        left_items = [item for item in items if str(item["event"].get("staff", "")) == "left_hand"]
        source = left_items or items
        counts: dict[str, int] = {}
        for item in source:
            counts[str(item["accidental"])] = counts.get(str(item["accidental"]), 0) + 1
        # Prefer the harmonic staff spelling. If tied, natural is least
        # surprising; otherwise keep the most common spelling.
        return sorted(counts, key=lambda accidental: (-counts[accidental], accidental != "natural", accidental))[0]

    @staticmethod
    def _parse_pitch_token(pitch: str) -> dict[str, Any] | None:
        match = re.match(r"^([A-G])([#b]*)(-?\d+)$", str(pitch))
        if not match:
            return None
        step, accidental, octave_text = match.groups()
        return {
            "step": step,
            "accidental": accidental or "natural",
            "octave": int(octave_text),
        }

    @staticmethod
    def _spell_fixed_step_pitch(step: str, accidental: str, octave: int) -> str:
        marker = "" if accidental == "natural" else str(accidental)
        return f"{step}{marker}{int(octave)}"

    @staticmethod
    def _repair_final_augmented_unison_octaves(measure: dict[str, Any], key: str, mode: str) -> list[dict[str, Any]]:
        repairs: list[dict[str, Any]] = []
        for _pass in range(4):
            collision = SeraPipeline._first_final_augmented_collision(measure, key)
            if not collision:
                break
            target = collision["right"]
            event = target["event"]
            midi = int(target["midi"])
            context = [int(item["midi"]) for item in collision["sounding"] if item["event"] is not event]
            replacement = SeraPipeline._nearest_non_colliding_pitch(midi, context, key, mode)
            if replacement == midi:
                break
            before = str(event.get("pitch", ""))
            event["pitch"] = midi_to_pitch_name(replacement, key, mode)
            repairs.append(
                {
                    "measure": int(measure.get("number", 1) or 1),
                    "event_id": str(event.get("event_id", "")),
                    "from": before,
                    "to": event["pitch"],
                    "reason": "final_augmented_unison_or_octave_vertical_collision",
                }
            )
        return repairs

    @staticmethod
    def _first_final_augmented_collision(measure: dict[str, Any], key: str) -> dict[str, Any] | None:
        flattened = SeraPipeline._flatten_final_measure_events(measure, key)
        times = sorted({item["start"] for item in flattened} | {item["end"] for item in flattened})
        for time in times:
            sounding = [item for item in flattened if item["start"] <= time < item["end"]]
            for left_index, left in enumerate(sounding):
                for right in sounding[left_index + 1 :]:
                    if left["staff"] == right["staff"] and left["voice"] == right["voice"]:
                        continue
                    if not SeraPipeline._is_augmented_unison_or_octave(left["midi"], right["midi"], key):
                        continue
                    right_item = left if left["staff"] != "left_hand" else right if right["staff"] != "left_hand" else right
                    return {"right": right_item, "left": right if right_item is left else left, "sounding": sounding}
        return None

    @staticmethod
    def _flatten_final_measure_events(measure: dict[str, Any], key: str) -> list[dict[str, Any]]:
        del key
        flattened: list[dict[str, Any]] = []
        for event in measure.get("events", []):
            if event.get("type") == "rest":
                continue
            midi = parse_pitch_name(str(event.get("pitch", "")))
            if midi is None:
                continue
            start = float(event.get("offset", 0.0) or 0.0)
            duration = SeraPipeline._duration_to_quarters(str(event.get("duration", "quarter")))
            flattened.append(
                {
                    "event": event,
                    "midi": midi,
                    "staff": str(event.get("staff", "right_hand")),
                    "voice": int(event.get("voice", 1) or 1),
                    "start": start,
                    "end": start + duration,
                }
            )
        return flattened

    @staticmethod
    def _is_augmented_unison_or_octave(first_midi: int, second_midi: int, key: str) -> bool:
        first = SeraPipeline._spelled_pitch_info(first_midi, key)
        second = SeraPipeline._spelled_pitch_info(second_midi, key)
        lower, upper = (first, second) if first["midi"] <= second["midi"] else (second, first)
        return (upper["letter"] - lower["letter"]) % 7 == 0 and (upper["midi"] - lower["midi"]) % 12 == 1

    @staticmethod
    def _spelled_pitch_info(midi: int, key: str) -> dict[str, int]:
        pitch = midi_to_pitch_name(int(midi), key)
        match = re.match(r"^([A-G])([#b]*)(-?\d+)$", pitch)
        if not match:
            return {"midi": int(midi), "letter": 0}
        step, _accidental, octave_text = match.groups()
        step_index = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}.get(step, 0)
        return {"midi": int(midi), "letter": step_index + 7 * int(octave_text)}

    @staticmethod
    def _nearest_non_colliding_pitch(original: int, context: list[int], key: str, mode: str) -> int:
        allowed = SeraPipeline._allowed_melodic_pitch_classes(key, mode)
        candidates = [original + delta for delta in (1, -1, 2, -2, 3, -3, 4, -4)]
        candidates = [item for item in candidates if 48 <= item <= 88]
        candidates.sort(key=lambda item: (0 if item % 12 in allowed else 1, abs(item - original), item))
        for candidate in candidates:
            if any(SeraPipeline._is_augmented_unison_or_octave(candidate, other, key) for other in context):
                continue
            return int(candidate)
        return int(original)

    @staticmethod
    def _nearest_pitch_class_in_register(midi: int, target_pc: int) -> int:
        candidates = [((octave + 1) * 12 + int(target_pc) % 12) for octave in range(1, 8)]
        return int(min(candidates, key=lambda item: (abs(item - int(midi)), item)))

    @staticmethod
    def _allowed_melodic_pitch_classes(key: str, mode: str) -> set[int]:
        tonic = SeraPipeline._key_tonic_pc(key)
        scale = [0, 2, 3, 5, 7, 8, 10, 11] if mode == "minor" else [0, 2, 4, 5, 7, 9, 11]
        return {(tonic + item) % 12 for item in scale}

    @staticmethod
    def _key_tonic_pc(key: str) -> int:
        token = str(key or "C").split()[0].replace("-flat", "b")
        if not token:
            return 0
        step = token[0].upper()
        alter = 0
        if len(token) > 1:
            if token[1] == "#":
                alter = 1
            elif token[1].lower() == "b":
                alter = -1
        return ({"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}.get(step, 0) + alter) % 12

    @staticmethod
    def _clean_roman_symbol(chord_symbol: str) -> str:
        return (
            str(chord_symbol or "I")
            .replace("maj9", "")
            .replace("maj7", "")
            .replace("add9", "")
            .replace("7alt", "7")
            .replace("(add2)", "")
            .replace("(add4)", "")
            .replace("5", "")
        )

    @staticmethod
    def _duration_to_quarters(duration: str) -> float:
        return {
            "whole": 4.0,
            "half": 2.0,
            "quarter": 1.0,
            "eighth": 0.5,
            "sixteenth": 0.25,
            "16th": 0.25,
            "dotted_quarter": 1.5,
            "dotted_eighth": 0.75,
            "dotted_half": 3.0,
        }.get(str(duration).replace("-", "_"), 1.0)

    @staticmethod
    def _apply_generation_metadata_to_score_document(score_document: dict[str, Any], metadata: dict[str, Any]) -> None:
        """Preserve phrase/cadence/style metadata on the canonical score."""

        cadence_measures = {
            int(item.get("measure", 0)): str(item.get("cadence", "none"))
            for item in (metadata.get("cadence", {}) or {}).get("measures", [])
            if item.get("measure")
        }
        rhythm_measures = {
            int(item.get("measure", 0)): item
            for item in (metadata.get("rhythm_patterns", {}) or {}).get("measures", [])
            if item.get("measure")
        }
        texture_measures = {
            int(item.get("measure", 0)): item
            for item in (metadata.get("texture", {}) or {}).get("measures", [])
            if item.get("measure")
        }
        phrase_measures = {
            int(item.get("measure", 0)): item
            for item in (metadata.get("phrase_melody", {}) or {}).get("measures", [])
            if item.get("measure")
        }
        for measure in score_document.get("measures", []):
            number = int(measure.get("number", 0) or 0)
            if number in cadence_measures:
                measure["cadence"] = cadence_measures[number]
            measure.setdefault("metadata", {})
            if number in rhythm_measures:
                measure["metadata"]["rhythm_pattern"] = rhythm_measures[number].get("pattern_id", "")
            if number in texture_measures:
                measure["metadata"]["texture"] = texture_measures[number].get("texture", "")
            if number in phrase_measures:
                phrase = phrase_measures[number]
                measure["metadata"]["phrase_melody"] = {
                    "phrase_id": phrase.get("phrase_id", ""),
                    "phrase_role": phrase.get("phrase_role", ""),
                    "motif_transform": phrase.get("motif_transform", ""),
                    "contour_type": phrase.get("contour_type", ""),
                    "call_response_role": phrase.get("call_response_role", ""),
                    "target_tones": phrase.get("target_tones", {}),
                }

    def _combined_validation(
        self,
        plan: CompositionPlan,
        musicxml: str,
        artifacts: GenerationArtifacts | None = None,
    ) -> ValidationResult:
        xml_result = self.musicxml_validator.validate_text(
            musicxml,
            plan=plan,
            midi_path=artifacts.midi_path if artifacts else None,
            pdf_path=artifacts.pdf_path if artifacts else None,
        )
        theory_result = self.theory_validator.validate_plan(plan)
        return ValidationResult(
            valid=xml_result.valid and theory_result.valid,
            issues=xml_result.issues + theory_result.issues,
            warnings=xml_result.warnings + theory_result.warnings,
            metrics=xml_result.metrics | theory_result.metrics,
        )

    def _write_artifacts(self, run_id: str, plan: CompositionPlan, generated: Any) -> GenerationArtifacts:
        musicxml_path = self.artifact_path(run_id, "musicxml")
        midi_path = self.artifact_path(run_id, "midi")
        abc_path = self.artifact_path(run_id, "abc")
        pdf_path = self.artifact_path(run_id, "pdf")
        experiment_dir = self.logger.experiment_dir(run_id)
        experiment_musicxml = experiment_dir / "generated.musicxml"
        experiment_midi = experiment_dir / "generated.mid"
        experiment_pdf = experiment_dir / "generated.pdf"
        plan_json = experiment_dir / "plan.json"
        validation_report = experiment_dir / "validation_report.json"
        metadata = experiment_dir / "metadata.json"
        revision_history = experiment_dir / "revision_history.json"
        experiment_log = experiment_dir / "experiment_log.json"

        self.musicxml_exporter.write_musicxml(generated.musicxml, musicxml_path)
        self.musicxml_exporter.write_musicxml(generated.musicxml, experiment_musicxml)
        self.musicxml_exporter.write_abc(generated.abc, abc_path)
        self.midi_exporter.write_midi(generated.note_events, plan.intent.tempo_bpm, midi_path)
        self.midi_exporter.write_midi(generated.note_events, plan.intent.tempo_bpm, experiment_midi)
        self.pdf_exporter.write_pdf(musicxml_path, pdf_path, f"Sera {run_id}")
        self.pdf_exporter.write_pdf(experiment_musicxml, experiment_pdf, f"Sera {run_id}")
        self.logger.write_json(plan_json, plan.to_dict())

        export_files = [
            str(musicxml_path),
            str(midi_path),
            str(pdf_path),
            str(abc_path),
            str(plan_json),
            str(validation_report),
            str(experiment_log),
        ]
        return GenerationArtifacts(
            run_id=run_id,
            musicxml_path=str(musicxml_path),
            midi_path=str(midi_path),
            abc_path=str(abc_path),
            pdf_path=str(pdf_path),
            musicxml=generated.musicxml,
            abc=generated.abc,
            note_events=generated.note_events,
            plan_json_path=str(plan_json),
            validation_report_path=str(validation_report),
            experiment_dir=str(experiment_dir),
            metadata_path=str(metadata),
            revision_history_path=str(revision_history),
            experiment_log_path=str(experiment_log),
            export_files=export_files,
        )

    @staticmethod
    def _metadata(
        prompt: str,
        plan: CompositionPlan,
        artifacts: GenerationArtifacts,
        validation: ValidationResult,
        revision: dict[str, Any],
        generated: GeneratedScore,
    ) -> dict[str, Any]:
        generation = dict(generated.metadata or {})
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "model_provider": plan.intent.llm_provider,
            "agent_mode": plan.intent.agent_mode,
            "generator_mode": generation.get("generator_mode", "rule_based"),
            "symbolic_model": {
                "name": generation.get("model_name", ""),
                "backend": generation.get("model_backend", ""),
                "loaded": bool(generation.get("model_loaded", False)),
                "checkpoint_path": generation.get("checkpoint_path", ""),
            },
            "prompt": prompt,
            "raw_prompt": plan.intent.raw_prompt or prompt,
            "ui_controls": dict(plan.intent.ui_controls),
            "prompt_terms": list(plan.intent.prompt_terms),
            "source_prompt_terms": list(plan.intent.source_prompt_terms),
            "source_control_terms": list(plan.intent.source_control_terms),
            "intent_source": plan.intent.intent_source,
            "control_only_intent": bool(plan.intent.control_only_intent),
            "unparsed_prompt_terms": list(plan.intent.unparsed_prompt_terms),
            "prompt_ui_conflicts": list(plan.intent.prompt_ui_conflicts),
            "resolved_generation_request": dict(plan.intent.resolved_generation_request),
            "prompt_plan_alignment_score": float(plan.intent.prompt_plan_alignment_score),
            "style": plan.intent.style,
            "base_style": plan.intent.base_style,
            "custom_style_tags": plan.intent.custom_style_tags,
            "style_profile": plan.intent.style_profile,
            "run_seed": int(getattr(plan.intent, "run_seed", 0) or 0),
            "seed_source": getattr(plan.intent, "seed_source", ""),
            "variant_id": getattr(plan.intent, "variant_id", ""),
            "generation_nonce": getattr(plan.intent, "generation_nonce", ""),
            "key": plan.intent.key,
            "meter": plan.intent.time_signature,
            "tempo": plan.intent.tempo_bpm,
            "length_measures": plan.intent.bars,
            "export_files": artifacts.export_files,
            "validation_passed": validation.valid,
            "revision_changes": revision.get("changes", []),
            "generation_warnings": generation.get("warnings", []),
            "model_task_type": generation.get("model_task_type", ""),
            "decoding": generation.get("decoding", {}),
            "postprocess_report": generation.get("postprocess_report", {}),
            "metadata_sync_report": generation.get("metadata_sync_report", {}),
            "key_consistency_report": generation.get("key_consistency_report", {}),
            "melody_line_report": generation.get("melody_line_report", {}),
            "cross_measure_melodic_grammar_report": generation.get("cross_measure_melodic_grammar_report", {}),
            "melody_expectation_report": generation.get("melody_expectation_report", {}),
            "phrase_melody": generation.get("phrase_melody", {}),
            "motif_memory_report": generation.get("motif_memory_report", {}),
            "phrase_contour_report": generation.get("phrase_contour_report", {}),
            "target_tone_report": generation.get("target_tone_report", {}),
            "tension_release_report": generation.get("tension_release_report", {}),
            "accompaniment_interaction_report": generation.get("accompaniment_interaction_report", {}),
            "candidate_generation": generation.get("candidate_generation", {}),
            "candidate_rank_report": generation.get("candidate_rank_report", {}),
            "harmony_profile": generation.get("harmony_profile", {}),
            "voicing_report": generation.get("voicing_report", {}),
            "voice_leading_report": generation.get("voice_leading_report", {}),
            "harmony_style_score": generation.get("harmony_style_score", 0.0),
            "track_plan": generation.get("track_plan", []),
            "role_coverage_report": generation.get("role_coverage_report", {}),
            "notation_normalization_report": generation.get("notation_normalization_report", {}),
            "notation_validation_report": generation.get("notation_validation_report", {}),
            "musicality_validation_report": generation.get("musicality_validation_report", {}),
            "preview_render": generation.get("preview_render", {}),
            "generation_profile": generation.get("generation_profile", {}),
            "rhythm_patterns": generation.get("rhythm_patterns", {}),
            "motifs": generation.get("motifs", {}),
            "harmony_plan_v09": generation.get("harmony_plan", {}),
            "texture_plan": generation.get("texture", {}),
            "cadence_plan": generation.get("cadence", {}),
            "accompaniment_plan": generation.get("accompaniment", {}),
            "fallback_reason": generation.get("fallback_reason", ""),
        }

    @staticmethod
    def _normalize_rating(rating: dict[str, Any]) -> dict[str, Any]:
        """Clamp human evaluation fields to paper-ready 1-5 score ranges."""

        score_keys = [
            "prompt_adherence",
            "musical_coherence",
            "notation_readability",
            "playability",
            "editability",
        ]
        scores: dict[str, int] = {}
        for key in score_keys:
            value = rating.get(key, 0)
            try:
                scores[key] = max(1, min(5, int(value)))
            except (TypeError, ValueError):
                scores[key] = 3
        average = sum(scores.values()) / len(scores)
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            **scores,
            "average_score": round(average, 3),
            "preference": str(rating.get("preference", "no_preference"))[:80],
            "notes": str(rating.get("notes", ""))[:2000],
            # TODO: add anonymized participant/session identifiers for IRB-style
            # human studies instead of storing only a single local rating object.
            "rater_id": str(rating.get("rater_id", "local_demo"))[:80],
        }

    @staticmethod
    def _revision_history(
        previous_record: dict[str, Any] | None,
        plan: CompositionPlan,
        revision: dict[str, Any],
        validation_before_revision: ValidationResult,
    ) -> dict[str, Any]:
        return {
            "previous_run_id": previous_record.get("run_id") if previous_record else None,
            "feedback": revision.get("feedback", ""),
            "changes": revision.get("changes", []),
            "validation_before_revision": validation_before_revision.to_dict(),
            "old_version": previous_record.get("plan") if previous_record else revision.get("old_plan_summary", {}),
            "new_version": plan.to_dict(),
        }

    @staticmethod
    def _record(
        run_id: str,
        prompt: str,
        plan: CompositionPlan,
        artifacts: GenerationArtifacts,
        validation: ValidationResult,
        revision: dict[str, Any],
        evaluation: dict[str, Any],
        metadata: dict[str, Any],
        generated: GeneratedScore,
    ) -> dict[str, Any]:
        try:
            score_document = generated.score_document or musicxml_to_score_document(generated.musicxml, prompt=prompt, source="generated")
            score_document.setdefault("metadata", {})["generation_metadata"] = generated.metadata or {}
            score_document.setdefault("metadata", {})["v09_profile"] = (generated.metadata or {}).get("generation_profile", {})
        except Exception:  # noqa: BLE001 - generation records must remain writable.
            score_document = {}
        consistency_report = ScoreConsistencyService().build_report(
            musicxml=generated.musicxml,
            score_document=score_document,
            midi_note_events=generated.note_events,
            midi_path=artifacts.midi_path,
        )
        key_consistency_report = KeyConsistencyService().build_report(
            intent=plan.intent.to_dict(),
            resolved_controls=dict((plan.intent.resolved_generation_request or {}).get("resolved_controls", {})),
            score_document=score_document,
            musicxml=generated.musicxml,
            metadata_sync_report=(generated.metadata or {}).get("metadata_sync_report", {}),
        )
        exports = {
            "musicxml": f"/export/{run_id}/musicxml",
            "midi": f"/export/{run_id}/midi",
            "pdf": f"/export/{run_id}/pdf",
            "abc": f"/export/{run_id}/abc",
        }
        preview_render = (generated.metadata or {}).get("preview_render", {})
        return {
            "run_id": run_id,
            "prompt": prompt,
            "raw_prompt": plan.intent.raw_prompt or prompt,
            "intent": plan.intent.to_dict(),
            "plan": plan.to_dict(),
            "prompt_control_resolution": {
                "raw_prompt": plan.intent.raw_prompt or prompt,
                "ui_controls": dict(plan.intent.ui_controls),
                "resolved_controls": dict((plan.intent.resolved_generation_request or {}).get("resolved_controls", {})),
                "conflicts": list(plan.intent.prompt_ui_conflicts),
                "defaults_used": list((plan.intent.resolved_generation_request or {}).get("defaults_used", [])),
                "warnings": list((plan.intent.resolved_generation_request or {}).get("warnings", [])),
                "intent_source": plan.intent.intent_source,
                "source_control_terms": list(plan.intent.source_control_terms),
                "control_only_intent": bool(plan.intent.control_only_intent),
                "prompt_terms": list(plan.intent.prompt_terms),
                "source_prompt_terms": list(plan.intent.source_prompt_terms),
                "unparsed_prompt_terms": list(plan.intent.unparsed_prompt_terms),
                "prompt_plan_alignment_score": float(plan.intent.prompt_plan_alignment_score),
            },
            "musicxml": generated.musicxml,
            "score_document": score_document,
            "midi_url": exports["midi"],
            "exports": exports,
            "generation_metadata": generated.metadata or {},
            "consistency_report": consistency_report,
            "key_consistency_report": key_consistency_report,
            "preview_render": preview_render,
            "backend_rendered_svg_url": preview_render.get("svg_url", ""),
            "backend_rendered_png_url": preview_render.get("png_url", ""),
            "artifacts": artifacts.to_dict(),
            "validation": validation.to_dict(),
            "validation_report": validation.to_report(),
            "revision": revision,
            "evaluation": evaluation,
            "metadata": metadata,
            "generation": generated.metadata or {},
            "user_rating": None,
        }

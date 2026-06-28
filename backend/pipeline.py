"""End-to-end Sera generation pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.agents.prompt_understanding_agent import PromptUnderstandingAgent
from backend.agents.revision_agent import RevisionAgent
from backend.export.midi_exporter import MidiExporter
from backend.export.musicxml_exporter import MusicXMLExporter
from backend.export.pdf_exporter import PDFExporter
from backend.generation.model_generator import ModelGenerator
from backend.generation.symbolic_generator import SymbolicMusicGenerator
from backend.models.schemas import CompositionPlan, GenerationArtifacts, ValidationResult
from backend.storage.experiment_logger import ExperimentLogger
from backend.validation.musicxml_validator import MusicXMLValidator
from backend.validation.theory_validator import TheoryValidator


class SeraPipeline:
    """Coordinate prompt agents, symbolic generation, validation, and logging."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.prompt_agent = PromptUnderstandingAgent()
        self.planning_agent = CompositionPlanningAgent()
        self.generator = SymbolicMusicGenerator()
        self.musicxml_validator = MusicXMLValidator()
        self.theory_validator = TheoryValidator()
        self.revision_agent = RevisionAgent()
        self.musicxml_exporter = MusicXMLExporter()
        self.midi_exporter = MidiExporter()
        self.pdf_exporter = PDFExporter()
        self.logger = ExperimentLogger(self.project_root)
        self.model_lab = ModelGenerator(self.project_root)

    def generate(self, prompt: str) -> dict[str, Any]:
        """Run the full generation pipeline and persist all artifacts."""

        intent = self.prompt_agent.understand(prompt)
        plan = self.planning_agent.plan(intent)
        return self._persist_generated_plan(prompt=prompt, plan=plan)

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

        return self.model_lab.status()

    def symbolic_model_sample(self, prompt: str, max_tokens: int = 96) -> dict[str, Any]:
        """Generate or replay a qualitative symbolic-model token sample."""

        return self.model_lab.sample_tokens(prompt, max_tokens=max_tokens)

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
    ) -> dict[str, Any]:
        generated = self.generator.generate(plan)
        preliminary = self._combined_validation(plan, generated.musicxml)
        revision = revision or {
            "agent": "revision_agent_v0_2",
            "feedback": "",
            "changes": ["no structural repair required"],
            "valid_before_revision": preliminary.valid,
        }

        if not preliminary.valid and previous_record is None:
            repaired_plan, revision = self.revision_agent.revise(plan, preliminary)
            plan = repaired_plan
            generated = self.generator.generate(plan)
            preliminary = self._combined_validation(plan, generated.musicxml)

        run_id = self.logger.new_run_id(prompt)
        artifacts = self._write_artifacts(run_id, plan, generated)
        prompt_path = Path(artifacts.experiment_dir) / "prompt.txt"
        self.logger.write_text(prompt_path, prompt)
        artifacts.export_files.append(str(prompt_path))
        validation = self._combined_validation(plan, generated.musicxml, artifacts)
        evaluation = self.evaluate_payload(plan, validation, revision)

        self.logger.write_json(artifacts.validation_report_path, validation.to_report())
        metadata = self._metadata(prompt, plan, artifacts, validation, revision)
        self.logger.write_json(artifacts.metadata_path, metadata)
        self.logger.write_json(
            artifacts.revision_history_path,
            self._revision_history(previous_record, plan, revision, preliminary),
        )

        record = self._record(run_id, prompt, plan, artifacts, validation, revision, evaluation, metadata)
        self.logger.write_json(artifacts.experiment_log_path, record)
        self.logger.append(record)
        return record | {"musicxml": generated.musicxml, "abc": generated.abc}

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
    ) -> dict[str, Any]:
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "model_provider": plan.intent.llm_provider,
            "agent_mode": plan.intent.agent_mode,
            "generator_mode": "rule_based",
            "prompt": prompt,
            "style": plan.intent.style,
            "key": plan.intent.key,
            "meter": plan.intent.time_signature,
            "tempo": plan.intent.tempo_bpm,
            "length_measures": plan.intent.bars,
            "export_files": artifacts.export_files,
            "validation_passed": validation.valid,
            "revision_changes": revision.get("changes", []),
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
    ) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "prompt": prompt,
            "intent": plan.intent.to_dict(),
            "plan": plan.to_dict(),
            "artifacts": artifacts.to_dict(),
            "validation": validation.to_dict(),
            "validation_report": validation.to_report(),
            "revision": revision,
            "evaluation": evaluation,
            "metadata": metadata,
            "user_rating": None,
        }

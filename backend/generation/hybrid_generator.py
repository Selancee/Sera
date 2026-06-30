"""Sera V0.5 hybrid generator.

The agent plans structure, the rule-based generator assembles legal MusicXML,
and the optional small model only contributes local musical fragments.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.generation.model_generator import ModelGenerator
from backend.generation.postprocess import postprocess_structured_events
from backend.generation.rule_based_generator import GeneratedScore, RuleBasedGenerator
from backend.models.schemas import CompositionPlan
from backend.validation.musicxml_validator import MusicXMLValidator
from evaluation.analysis.music_statistics import parse_musicxml_notes
from training.tokenization.musicxml_to_structured_events import musicxml_to_structured_events
from training.tokenization.structured_events import decode_note_token
from training.tokenization.structured_events_to_musicxml import structured_events_to_musicxml


class HybridV05Generator:
    """Generate legal MusicXML with local model-assisted musicality."""

    def __init__(self, project_root: str | Path | None = None, enable_postprocess: bool = True) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.rule_based = RuleBasedGenerator()
        self.model_generator = ModelGenerator(self.project_root)
        self.validator = MusicXMLValidator()
        self.enable_postprocess = enable_postprocess

    def generate(self, plan: CompositionPlan) -> GeneratedScore:
        """Return a V0.5 hybrid score with explicit fallback metadata."""

        working_plan = plan
        fragments: list[dict[str, Any]] = []
        fallback_reasons: list[str] = []
        for measure in working_plan.measures:
            task_type = "cadence_generation" if measure.cadence in {"half", "authentic"} else "melody_fragment"
            fragment = self.model_generator.generate_task_fragment(working_plan, measure.index, task_type=task_type)
            fragments.append(fragment)
            if fragment.get("fallback_reason"):
                fallback_reasons.append(str(fragment["fallback_reason"]))
            degree_hints = self._fragment_to_degree_hints(fragment.get("tokens", []), working_plan.intent.key)
            if degree_hints:
                measure.notes = degree_hints[: max(2, len(measure.notes))]

        generated = self.rule_based.generate(working_plan)
        postprocess_report: dict[str, Any] = {
            "enabled": self.enable_postprocess,
            "actions": [],
            "used_processed_musicxml": False,
        }
        if self.enable_postprocess:
            generated, postprocess_report = self._postprocess_generated(generated, working_plan)

        generated.musicxml = generated.musicxml.replace(
            "Sera rule-based generator V0.2",
            "Sera hybrid generator V0.5",
        )
        generated.metadata = {
            **(generated.metadata or {}),
            "generator_mode": "hybrid_v05" if self.enable_postprocess else "hybrid_v05_no_postprocess",
            "model_task_type": "melody_fragment",
            "generated_fragment": fragments[:8],
            "postprocess_report": postprocess_report,
            "fallback_reason": "; ".join(sorted(set(fallback_reasons))) if fallback_reasons else "",
            "final_validation_report": {},
            "decoding": {
                "temperature": 1.15,
                "top_p": 0.92,
                "top_k": 60,
                "repetition_penalty": 1.2,
                "no_repeat_ngram_size": 4,
                "max_consecutive_same_duration": 3,
                "max_consecutive_stepwise_motion": 4,
            },
        }
        plan.baseline = "hybrid_v05"
        return generated

    def _postprocess_generated(self, generated: GeneratedScore, plan: CompositionPlan) -> tuple[GeneratedScore, dict[str, Any]]:
        try:
            structured = musicxml_to_structured_events(generated.musicxml)
            processed_events, report = postprocess_structured_events(structured.events)
            processed_xml = structured_events_to_musicxml(processed_events, title=plan.intent.title)
            validation = self.validator.validate_text(processed_xml, plan=plan)
            report["enabled"] = True
            report["used_processed_musicxml"] = validation.valid
            report["validation_after_postprocess"] = validation.to_report()
            if validation.valid:
                return (
                    GeneratedScore(
                        musicxml=processed_xml,
                        abc=generated.abc,
                        note_events=self._note_events_from_musicxml(processed_xml, plan),
                        metadata=generated.metadata,
                    ),
                    report,
                )
            report.setdefault("actions", []).append("postprocess output rejected by validator; kept rule-based MusicXML")
            return generated, report
        except Exception as exc:  # noqa: BLE001 - hybrid must keep legal fallback.
            return generated, {
                "enabled": True,
                "used_processed_musicxml": False,
                "actions": [f"postprocess failed; kept rule-based MusicXML: {exc}"],
            }

    @staticmethod
    def _fragment_to_degree_hints(tokens: list[str], key: str) -> list[str]:
        pitches = []
        for token in tokens:
            if not str(token).startswith("NOTE_"):
                continue
            pitches.append((decode_note_token(str(token)) or "C4").replace("SHARP", "#").replace("FLAT", "b"))
        return ModelGenerator._pitch_names_to_degrees(pitches, key)

    @staticmethod
    def _note_events_from_musicxml(musicxml: str, plan: CompositionPlan) -> list[dict[str, Any]]:
        notes = parse_musicxml_notes(musicxml)
        beats, beat_type = [int(part) for part in plan.intent.time_signature.split("/")]
        measure_quarters = beats * (4 / beat_type)
        events: list[dict[str, Any]] = []
        for note in notes:
            if note.midi is None:
                continue
            events.append(
                {
                    "measure": note.measure,
                    "pitch": note.pitch,
                    "midi": note.midi,
                    "start_quarter": (note.measure - 1) * measure_quarters + note.offset_quarter,
                    "duration_quarter": note.duration_quarter,
                    "velocity": 72,
                    "voice": int(note.voice) if str(note.voice).isdigit() else 1,
                    "staff": int(note.staff) if str(note.staff).isdigit() else 1,
                }
            )
        return events

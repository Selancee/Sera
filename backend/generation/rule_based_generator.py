"""Rule-based symbolic generator for Sera V0.2.

The generator favors legal, parseable MusicXML over complex notation.  It can
emit a piano single-line sketch or a simplified two-staff piano texture using
deterministic motifs, phrase repetition, basic harmony, and cadences.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Any

from backend.generation.musicality.accompaniment_engine import AccompanimentEngine
from backend.generation.musicality.accompaniment_interaction import plan_accompaniment_interaction
from backend.generation.musicality.cadence_engine import CadenceEngine
from backend.generation.musicality.dynamics_engine import DynamicsEngine
from backend.generation.musicality.expectation_melody_engine import generate_expectation_melody
from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.harmony_engine import HarmonyEngine
from backend.generation.musicality.melody_candidate_ranker import rank_melody_candidates
from backend.generation.musicality.melodic_grammar import repair_melodic_line, validate_melodic_line
from backend.generation.musicality.melodic_style_engine import build_melodic_style_profile, generate_phrase_degree_labels
from backend.generation.musicality.motif_engine import MotifEngine
from backend.generation.musicality.musicality_postprocessor import MusicalityPostprocessor
from backend.generation.musicality.phrase_melody_engine import generate_period_melody
from backend.generation.musicality.pitch_spelling import midi_to_pitch_name
from backend.generation.musicality.rhythm_engine import RhythmEngine
from backend.generation.musicality.texture_engine import TextureEngine
from backend.generation.seed_service import create_run_seed, create_variant_id, make_seeded_rng
from backend.models.schemas import CompositionPlan, MeasurePlan


STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MAJOR_DEGREES = {"1": 0, "b2": 1, "2": 2, "b3": 3, "3": 4, "4": 5, "#4": 6, "b5": 6, "5": 7, "b6": 8, "6": 9, "b7": 10, "7": 11}
MINOR_DEGREES = {"1": 0, "b2": 1, "2": 2, "b3": 3, "3": 3, "4": 5, "#4": 6, "b5": 6, "5": 7, "b6": 8, "6": 8, "b7": 10, "7": 11}
SEMITONE_TO_PITCH = {
    0: ("C", 0),
    1: ("C", 1),
    2: ("D", 0),
    3: ("E", -1),
    4: ("E", 0),
    5: ("F", 0),
    6: ("F", 1),
    7: ("G", 0),
    8: ("A", -1),
    9: ("A", 0),
    10: ("B", -1),
    11: ("B", 0),
}


@dataclass(slots=True)
class GeneratedScore:
    """In-memory symbolic score payloads."""

    musicxml: str
    abc: str
    note_events: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)
    score_document: dict[str, Any] = field(default_factory=dict)


class RuleBasedGenerator:
    """Generate legal 8, 16, or 32 measure MusicXML from a composition plan."""

    def generate(self, plan: CompositionPlan) -> GeneratedScore:
        """Return MusicXML, ABC, and note events for the supplied plan."""

        intent = plan.intent
        profile = GenerationProfile.from_plan(plan)
        self._ensure_profile_seed(intent, profile)
        time = self._time_info(intent.time_signature)
        tonic = self._tonic(intent.key)
        tonic_pc = self._tonic_pc(tonic)
        mode = "minor" if "minor" in intent.key.lower() else "major"
        two_staff = self._use_two_staff(intent.instruments, profile.texture, profile.requires_accompaniment)
        style_profile_payload = dict(profile.style_profile or {})
        style_profile_payload.setdefault("base_style", profile.base_style)
        style_profile_payload.setdefault("custom_style_tags", list(profile.custom_style_tags or []))
        style_profile_payload.setdefault("texture", profile.texture)
        style_profile_payload.setdefault("harmony_flavor", profile.harmony_flavor)
        melodic_style_profile = build_melodic_style_profile(style_profile_payload, profile.key, mode, profile.difficulty)
        rhythm_metadata = RhythmEngine().generate(profile, len(plan.measures))
        motif_metadata = MotifEngine().generate(profile, len(plan.measures))
        harmony_metadata = HarmonyEngine().generate(profile, len(plan.measures))
        cadence_metadata = CadenceEngine().generate(profile, len(plan.measures))
        texture_metadata = TextureEngine().generate(profile, len(plan.measures))
        dynamics_metadata = DynamicsEngine().generate(profile, len(plan.measures))
        accompaniment_metadata = AccompanimentEngine().generate(profile, list(harmony_metadata.get("chords", [])))
        phrase_melody_metadata = generate_period_melody(
            {
                "key": profile.key,
                "tonic_pc": tonic_pc,
                "mode": mode,
                "length_measures": len(plan.measures),
                "phrase_length_measures": 4,
                "measures": [
                    {
                        "measure": measure.index,
                        "section": measure.section,
                        "cadence": measure.cadence,
                    }
                    for measure in plan.measures
                ],
            },
            list(harmony_metadata.get("chords", [])),
            list(rhythm_metadata.get("measures", [])),
            {
                **dict(style_profile_payload or {}),
                "style": profile.style,
                "base_style": profile.base_style,
                "custom_style_tags": list(profile.custom_style_tags or []),
                "key": profile.key,
            },
            melodic_style_profile,
            {},
            make_seeded_rng(profile.run_seed or 1, f"phrase_melody:{profile.variation_seed}:{profile.variation_index}"),
        )
        phrase_melody_by_measure = {
            int(item.get("measure", 0) or 0): item
            for item in phrase_melody_metadata.get("measures", [])
            if item.get("measure")
        }
        accompaniment_interaction_metadata = plan_accompaniment_interaction(
            phrase_melody_metadata,
            list(harmony_metadata.get("chords", [])),
            {
                **dict(style_profile_payload or {}),
                **dict(melodic_style_profile or {}),
                "style": profile.style,
                "base_style": profile.base_style,
                "custom_style_tags": list(profile.custom_style_tags or []),
            },
            accompaniment_metadata,
            make_seeded_rng(profile.run_seed or 1, f"accompaniment_interaction:{profile.variation_seed}:{profile.variation_index}"),
        )

        measure_xml: list[str] = []
        abc_measures: list[str] = []
        note_events: list[dict[str, Any]] = []
        melodic_grammar_reports: list[dict[str, Any]] = []
        melody_generation_reports: list[dict[str, Any]] = []
        vertical_sonority_reports: list[dict[str, Any]] = []
        cursor_quarters = 0.0

        for measure in plan.measures:
            measure_index = max(0, measure.index - 1)
            measure.chord = str(harmony_metadata.get("chords", [measure.chord])[measure_index])
            cadence = str(cadence_metadata.get("measures", [{}])[measure_index].get("cadence", measure.cadence))
            measure.cadence = "authentic" if cadence in {"authentic", "modal_pentatonic_ending"} else "half" if cadence == "half" else "none"
            measure.texture = str(texture_metadata.get("measures", [{}])[measure_index].get("texture", profile.texture))
            rhythm_events = rhythm_metadata.get("measures", [{}])[measure_index].get("events", [])
            motif_degrees = motif_metadata.get("measures", [{}])[measure_index].get("degrees", measure.notes)
            dynamic = str(dynamics_metadata.get("measures", [{}])[measure_index].get("dynamic", "mf"))
            right_events = self._right_hand_events(
                measure,
                measure.texture,
                tonic_pc,
                mode,
                time,
                rhythm_events,
                motif_degrees,
                dynamic,
                melodic_style_profile=melodic_style_profile,
                profile=profile,
                grammar_reports=melodic_grammar_reports,
                melody_generation_reports=melody_generation_reports,
                phrase_melody_measure=phrase_melody_by_measure.get(measure.index),
            )
            left_events = self._left_hand_events_from_accompaniment(accompaniment_metadata.get("measures", [{}])[measure_index], time) if two_staff else []
            harmony_alignment_report = self._align_minor_harmony_and_melody(
                right_events,
                left_events,
                measure.chord,
                tonic_pc,
                mode,
                intent.key,
                measure.index,
            )
            vertical_report = self._repair_vertical_augmented_collisions(right_events, left_events, intent.key, mode, measure.index)
            if vertical_report.get("repair_count") or harmony_alignment_report.get("repair_count"):
                vertical_sonority_reports.append({**vertical_report, "harmony_alignment": harmony_alignment_report})
            self._assign_internal_beams(right_events, intent.time_signature, time)
            self._assign_internal_beams(left_events, intent.time_signature, time)
            measure_xml.append(
                self._measure_xml(
                    measure=measure,
                    right_events=right_events,
                    left_events=left_events,
                    key=intent.key,
                    time=time,
                    first_measure=measure.index == 1,
                    two_staff=two_staff,
                )
            )
            note_events.extend(
                self._events_to_midi_payload(right_events + left_events, measure.index, cursor_quarters, time, intent.key)
            )
            abc_measures.append(" ".join("z" if event.get("rest") else self._abc_note(self._pitch_name(event["pitches"][0], intent.key)) for event in right_events))
            cursor_quarters += time["quarter_total"]

        title = escape(intent.title or f"Sera draft - {intent.style}")
        part_name = "Piano" if two_staff else escape(intent.instruments[0])
        musicxml = "\n".join(
            [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
                '<score-partwise version="3.1">',
                "  <work>",
                f"    <work-title>{title}</work-title>",
                "  </work>",
                "  <identification>",
                "    <creator type=\"composer\">Sera rule-based generator V0.2</creator>",
                "  </identification>",
                "  <part-list>",
                "    <score-part id=\"P1\">",
                f"      <part-name>{part_name}</part-name>",
                "    </score-part>",
                "  </part-list>",
                "  <part id=\"P1\">",
                *measure_xml,
                "  </part>",
                "</score-partwise>",
                "",
            ]
        )
        abc = "\n".join(
            [
                "X:1",
                f"T:{intent.title}",
                f"M:{intent.time_signature}",
                "L:1/8",
                f"Q:1/4={intent.tempo_bpm}",
                f"K:{self._abc_key(intent.key)}",
                "| " + " | ".join(abc_measures) + " |",
                "",
            ]
        )
        phrase_used = any(item.get("source") == "phrase_melody_engine" for item in melody_generation_reports)
        expectation_used = any(item.get("source") == "expectation_engine" for item in melody_generation_reports)
        metadata = {
            "generator_mode": "rule_based_v09",
            "model_loaded": False,
            "generation_profile": profile.to_dict(),
            "rhythm_patterns": rhythm_metadata,
            "motifs": motif_metadata,
            "harmony_plan": harmony_metadata,
            "harmony_progression_source": harmony_metadata.get("harmony_progression_source", harmony_metadata.get("progression_source", "")),
            "style_progression_family": harmony_metadata.get("style_progression_family", ""),
            "selected_progression": harmony_metadata.get("selected_progression", harmony_metadata.get("progression", [])),
            "old_variation_override_used": bool(harmony_metadata.get("old_variation_override_used", False)),
            "texture": texture_metadata,
            "cadence": cadence_metadata,
            "accompaniment": accompaniment_metadata,
            "voicing_source": accompaniment_metadata.get("voicing_source", "static_chord_fallback"),
            "actual_voicing_pitches_by_measure": accompaniment_metadata.get("actual_voicing_pitches_by_measure", {}),
            "dynamics": dynamics_metadata,
            "melodic_style_profile": melodic_style_profile,
            "motif_source": motif_metadata.get("motif_source", ""),
            "pitch_vocabulary": melodic_style_profile.get("pitch_vocabulary", ""),
            "contour_policy": melodic_style_profile.get("contour_policy", ""),
            "interval_policy": melodic_style_profile.get("interval_policy", ""),
            "melodic_grammar_report": {
                "valid": all(item.get("after", {}).get("valid", False) for item in melodic_grammar_reports),
                "measures": melodic_grammar_reports,
            },
            "melody_generation": {
                "engine": "phrase_melody_engine_v0962",
                "measures": melody_generation_reports,
                "phrase_level": phrase_melody_metadata,
            },
            "melody_generation_source": "phrase_melody_engine" if phrase_used else "expectation_engine" if expectation_used else "fallback_degree_template",
            "selected_melody_candidate_index": melody_generation_reports[0].get("selected_melody_candidate_index", -1) if melody_generation_reports else -1,
            "melody_candidate_count": max([int(item.get("melody_candidate_count", 0) or 0) for item in melody_generation_reports] or [0]),
            "hardcoded_shape_fallback_used": not phrase_used,
            "fallback_reason": None if phrase_used else None if expectation_used else "phrase_melody_engine_not_available",
            "phrase_melody": phrase_melody_metadata,
            "motif_memory_report": phrase_melody_metadata.get("motif_memory_report", {}),
            "phrase_contour_report": phrase_melody_metadata.get("phrase_contour_report", {}),
            "target_tone_report": phrase_melody_metadata.get("target_tone_report", {}),
            "tension_release_report": phrase_melody_metadata.get("tension_release_report", {}),
            "accompaniment_interaction_report": accompaniment_interaction_metadata,
            "vertical_sonority_report": {
                "engine": "vertical_sonority_repair_v0962",
                "repair_count": sum(
                    int(item.get("repair_count", 0) or 0)
                    + int((item.get("harmony_alignment") or {}).get("repair_count", 0) or 0)
                    for item in vertical_sonority_reports
                ),
                "measures": vertical_sonority_reports,
            },
            "candidate_variation_profile": dict((getattr(intent, "resolved_generation_request", {}) or {}).get("candidate_variation_profile", {})),
        }
        metadata["postprocess_report"] = MusicalityPostprocessor().report_for_generated_metadata(profile, metadata)
        return GeneratedScore(
            musicxml=musicxml,
            abc=abc,
            note_events=note_events,
            metadata=metadata,
        )

    @staticmethod
    def _use_two_staff(instruments: list[str], texture: str, requires_accompaniment: bool = True) -> bool:
        if texture in {"single_line", "monophonic"} and not requires_accompaniment:
            return False
        return requires_accompaniment or any("piano" in instrument.lower() for instrument in instruments)

    @staticmethod
    def _ensure_profile_seed(intent: Any, profile: GenerationProfile) -> None:
        if profile.run_seed:
            return
        explicit = profile.variation_seed or ""
        controls = {"variation_seed": explicit} if explicit else {}
        profile.run_seed = create_run_seed(getattr(intent, "prompt", ""), controls)
        profile.seed_source = "user" if explicit else "backend_auto"
        profile.variant_id = profile.variant_id or create_variant_id(profile.run_seed)
        if not profile.variation_seed:
            profile.variation_seed = str(profile.run_seed)
        if hasattr(intent, "run_seed"):
            intent.run_seed = profile.run_seed
            intent.seed_source = profile.seed_source
            intent.variant_id = profile.variant_id
        if hasattr(intent, "constraints"):
            constraints = list(getattr(intent, "constraints", []))
            if not any(str(item).startswith("run_seed:") for item in constraints):
                constraints.append(f"run_seed:{profile.run_seed}")
            if not any(str(item).startswith("variation_seed:") for item in constraints):
                constraints.append(f"variation_seed:{profile.variation_seed}")
            intent.constraints = constraints

    @staticmethod
    def _time_info(signature: str) -> dict[str, Any]:
        beats, beat_type = [int(part) for part in signature.split("/")]
        divisions = 4
        expected = int(beats * divisions * (4 / beat_type))
        return {
            "beats": beats,
            "beat_type": beat_type,
            "divisions": divisions,
            "expected_duration": expected,
            "quarter_total": beats * (4 / beat_type),
        }

    def _right_hand_events(
        self,
        measure: MeasurePlan,
        texture: str,
        tonic_pc: int,
        mode: str,
        time: dict[str, Any],
        rhythm_events: list[dict[str, Any]] | None = None,
        degree_hints_override: list[str] | None = None,
        dynamic: str = "mf",
        melodic_style_profile: dict[str, Any] | None = None,
        profile: GenerationProfile | None = None,
        grammar_reports: list[dict[str, Any]] | None = None,
        melody_generation_reports: list[dict[str, Any]] | None = None,
        phrase_melody_measure: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        rhythm_events = rhythm_events or []
        if rhythm_events:
            durations = [max(1, int(round(float(item.get("duration_quarters", 1.0)) * time["divisions"]))) for item in rhythm_events]
            count = sum(1 for item in rhythm_events if not item.get("is_rest"))
        else:
            durations = self._melody_durations(
                time,
                measure.cadence,
                texture,
                getattr(measure, "rhythmic_density", measure.density),
                measure.index,
            )
            count = len(durations)
        melody: list[int] = []
        if melodic_style_profile and profile:
            phrase_role = "final" if measure.index == profile.length_measures else "cadence" if measure.cadence != "none" else "opening" if measure.section == "A" else "contrast"
            if phrase_melody_measure and phrase_melody_measure.get("midis"):
                ranked = self._rank_phrase_melody_measure(
                    measure=measure,
                    phrase_role=phrase_role,
                    mode=mode,
                    time=time,
                    durations=durations,
                    rhythm_events=rhythm_events,
                    melodic_style_profile=melodic_style_profile,
                    profile=profile,
                    count=max(1, count),
                    phrase_melody_measure=phrase_melody_measure,
                )
            else:
                ranked = self._rank_expectation_melody(
                    measure=measure,
                    phrase_role=phrase_role,
                    tonic_pc=tonic_pc,
                    mode=mode,
                    time=time,
                    durations=durations,
                    rhythm_events=rhythm_events,
                    melodic_style_profile=melodic_style_profile,
                    profile=profile,
                    count=max(1, count),
                )
            melody = list(ranked.get("melody", []))
            if grammar_reports is not None:
                grammar_reports.append(dict(ranked.get("grammar_report", {})))
            if melody_generation_reports is not None:
                melody_generation_reports.append(dict(ranked.get("generation_report", {})))
        if not melody:
            degree_hints = degree_hints_override or measure.notes
            melody = self._melody_pitches(
                degree_hints,
                tonic_pc,
                mode,
                max(1, count),
                measure.cadence,
                "style_locked" if melodic_style_profile else getattr(measure, "melodic_contour", "wave"),
                getattr(measure, "interval_profile", "mixed"),
            )
            if melodic_style_profile and profile:
                before = validate_melodic_line(melody, profile.key, mode, melodic_style_profile, profile.difficulty)
                repaired = repair_melodic_line(melody, profile.key, mode, melodic_style_profile, profile.difficulty)
                after = validate_melodic_line(repaired, profile.key, mode, melodic_style_profile, profile.difficulty)
                melody = repaired
                if grammar_reports is not None:
                    grammar_reports.append({"measure": measure.index, "before": before, "after": after})
                if melody_generation_reports is not None:
                    melody_generation_reports.append(
                        {
                            "measure": measure.index,
                            "source": "fallback_degree_template",
                            "selected_melody_candidate_index": -1,
                            "melody_candidate_count": 0,
                            "fallback_reason": "expectation_engine_returned_no_melody",
                        }
                    )
        if texture == "chordal":
            chord = self._chord_pitches(measure.chord, tonic_pc, mode, octave=4, low=57, high=84)
            return [
                self._event(chord, duration, 1, 1, offset, dynamic=dynamic)
                for offset, duration in self._offsets(durations)
            ]
        events: list[dict[str, Any]] = []
        melody_index = 0
        for rhythm_item, (offset, duration) in zip(rhythm_events or [{"is_rest": False}] * len(durations), self._offsets(durations), strict=False):
            if rhythm_item.get("is_rest"):
                events.append(self._event([], duration, 1, 1, offset, rest=True, dynamic=dynamic))
                continue
            pitch = melody[melody_index % len(melody)]
            melody_index += 1
            events.append(self._event([pitch], duration, 1, 1, offset, dynamic=dynamic))
        return events

    def _rank_phrase_melody_measure(
        self,
        measure: MeasurePlan,
        phrase_role: str,
        mode: str,
        time: dict[str, Any],
        durations: list[int],
        rhythm_events: list[dict[str, Any]],
        melodic_style_profile: dict[str, Any],
        profile: GenerationProfile,
        count: int,
        phrase_melody_measure: dict[str, Any],
    ) -> dict[str, Any]:
        note_offsets: list[float] = []
        note_durations: list[float] = []
        for rhythm_item, (offset, duration) in zip(rhythm_events or [{"is_rest": False}] * len(durations), self._offsets(durations), strict=False):
            if rhythm_item.get("is_rest"):
                continue
            note_offsets.append(offset / time["divisions"])
            note_durations.append(duration / time["divisions"])
        if not note_durations:
            return {"melody": [], "generation_report": {"measure": measure.index, "source": "fallback_degree_template", "fallback_reason": "rest_only_measure"}}

        phrase_count = max(1, min(count, len(note_durations)))
        midis = [int(item) for item in phrase_melody_measure.get("midis", []) if isinstance(item, int)]
        if not midis:
            return {"melody": [], "generation_report": {"measure": measure.index, "source": "fallback_degree_template", "fallback_reason": "phrase_melody_measure_empty"}}
        while len(midis) < phrase_count:
            midis.extend(midis)
        candidate_events = [
            self._melody_candidate_events(
                midis[:phrase_count],
                note_durations[:phrase_count],
                note_offsets[:phrase_count],
                measure.index,
                profile,
                mode,
                melodic_style_profile,
                repair=False,
            )
        ]
        style_payload = {
            **dict(profile.style_profile or {}),
            **dict(melodic_style_profile or {}),
            "style": profile.style,
            "base_style": profile.base_style,
            "custom_style_tags": list(profile.custom_style_tags or []),
            "key": profile.key,
        }
        ranked = rank_melody_candidates(candidate_events, harmony_context=[measure.chord], key=profile.key, style_profile=style_payload)
        selected_events = list(ranked.get("melody_events", []))
        selected_midis = [int(event.get("midi", 60) or 60) for event in selected_events] or midis[:phrase_count]
        before = validate_melodic_line(selected_midis, profile.key, mode, melodic_style_profile, profile.difficulty)
        after = validate_melodic_line(selected_midis, profile.key, mode, melodic_style_profile, profile.difficulty)
        phrase_scores = dict(phrase_melody_measure.get("phrase_level_scores") or {})
        return {
            "melody": selected_midis,
            "grammar_report": {
                "measure": measure.index,
                "before": before,
                "after": after,
                "selected_melody_candidate_index": 0,
                "phrase_melody_source": "phrase_melody_engine",
            },
            "generation_report": {
                "measure": measure.index,
                "source": "phrase_melody_engine",
                "selected_melody_candidate_index": int(ranked.get("selected_candidate_index", 0) or 0),
                "melody_candidate_count": len(candidate_events),
                "melody_expectation_report": ranked.get("melody_expectation_report", {}),
                "rejected_melody_candidates": ranked.get("rejected_melody_candidates", []),
                "style_family": melodic_style_profile.get("style_family", "default"),
                "fallback_reason": None,
                "hardcoded_shape_fallback_used": False,
                "phrase_id": phrase_melody_measure.get("phrase_id", ""),
                "phrase_role": phrase_melody_measure.get("phrase_role", phrase_role),
                "motif_transform": phrase_melody_measure.get("motif_transform", ""),
                "call_response_role": phrase_melody_measure.get("call_response_role", ""),
                "target_tones": phrase_melody_measure.get("target_tones", {}),
                "contour_type": phrase_melody_measure.get("contour_type", ""),
                "phrase_level_scores": phrase_scores,
            },
        }

    def _rank_expectation_melody(
        self,
        measure: MeasurePlan,
        phrase_role: str,
        tonic_pc: int,
        mode: str,
        time: dict[str, Any],
        durations: list[int],
        rhythm_events: list[dict[str, Any]],
        melodic_style_profile: dict[str, Any],
        profile: GenerationProfile,
        count: int,
    ) -> dict[str, Any]:
        note_offsets: list[float] = []
        note_durations: list[float] = []
        for rhythm_item, (offset, duration) in zip(rhythm_events or [{"is_rest": False}] * len(durations), self._offsets(durations), strict=False):
            if rhythm_item.get("is_rest"):
                continue
            note_offsets.append(offset / time["divisions"])
            note_durations.append(duration / time["divisions"])
        if not note_durations:
            return {"melody": [], "generation_report": {"measure": measure.index, "source": "fallback_degree_template", "fallback_reason": "rest_only_measure"}}

        style_payload = {
            **dict(profile.style_profile or {}),
            **dict(melodic_style_profile or {}),
            "style": profile.style,
            "base_style": profile.base_style,
            "custom_style_tags": list(profile.custom_style_tags or []),
            "key": profile.key,
        }
        candidate_events: list[list[dict[str, Any]]] = []
        candidate_sources: list[str] = []
        seed = profile.run_seed or create_run_seed(profile.key, {"variation_seed": profile.variation_seed})
        phrase_count = max(1, min(count, len(note_durations)))

        for variant_index in range(4):
            rng = make_seeded_rng(seed, f"expectation:{measure.index}:{phrase_role}:{profile.variation_index}:{variant_index}")
            generated = generate_expectation_melody(
                {
                    "key": profile.key,
                    "tonic_pc": tonic_pc,
                    "mode": mode,
                    "measure": measure.index,
                    "note_count": phrase_count,
                    "phrase_role": phrase_role,
                    "durations_quarters": note_durations[:phrase_count],
                    "variant_index": variant_index + profile.variation_index,
                    "contour": getattr(measure, "melodic_contour", "wave"),
                },
                [measure.chord],
                style_payload,
                melodic_style_profile,
                rng,
            )
            midis = [int(event.get("midi", 60) or 60) for event in generated.get("melody_events", [])][:phrase_count]
            candidate_events.append(self._melody_candidate_events(midis, note_durations, note_offsets, measure.index, profile, mode, melodic_style_profile))
            candidate_sources.append("expectation_engine")

        if not candidate_events:
            degree_rng = make_seeded_rng(seed, f"melody:fallback:{measure.index}:{phrase_role}:{profile.variation_index}")
            labels = generate_phrase_degree_labels(melodic_style_profile, phrase_role, phrase_count, degree_rng)
            degree_midis = self._melody_pitches(labels, tonic_pc, mode, phrase_count, measure.cadence, "style_locked", getattr(measure, "interval_profile", "mixed"))
            candidate_events.append(self._melody_candidate_events(degree_midis, note_durations, note_offsets, measure.index, profile, mode, melodic_style_profile))
            candidate_sources.append("fallback_degree_template")

        ranked = rank_melody_candidates(candidate_events, harmony_context=[measure.chord], key=profile.key, style_profile=style_payload)
        selected_events = list(ranked.get("melody_events", []))
        selected_midis = [int(event.get("midi", 60) or 60) for event in selected_events] or [60]
        selected_index = int(ranked.get("selected_candidate_index", -1) or 0)
        before = validate_melodic_line(selected_midis, profile.key, mode, melodic_style_profile, profile.difficulty)
        after = validate_melodic_line(selected_midis, profile.key, mode, melodic_style_profile, profile.difficulty)
        return {
            "melody": selected_midis,
            "grammar_report": {
                "measure": measure.index,
                "before": before,
                "after": after,
                "selected_melody_candidate_index": selected_index,
            },
            "generation_report": {
                "measure": measure.index,
                "source": candidate_sources[selected_index] if 0 <= selected_index < len(candidate_sources) else "expectation_engine",
                "selected_melody_candidate_index": selected_index,
                "melody_candidate_count": len(candidate_events),
                "melody_expectation_report": ranked.get("melody_expectation_report", {}),
                "rejected_melody_candidates": ranked.get("rejected_melody_candidates", []),
                "style_family": melodic_style_profile.get("style_family", "default"),
                "fallback_reason": None,
            },
        }

    def _melody_candidate_events(
        self,
        midis: list[int],
        note_durations: list[float],
        note_offsets: list[float],
        measure_index: int,
        profile: GenerationProfile,
        mode: str,
        melodic_style_profile: dict[str, Any],
        repair: bool = True,
    ) -> list[dict[str, Any]]:
        repaired = repair_melodic_line([int(item) for item in midis], profile.key, mode, melodic_style_profile, profile.difficulty) if repair else [int(item) for item in midis]
        while len(repaired) < len(note_durations):
            repaired.extend(repaired or [60])
        events = []
        for index, midi in enumerate(repaired[: len(note_durations)]):
            events.append(
                {
                    "type": "note",
                    "midi": int(midi),
                    "pitch": self._pitch_name(int(midi), profile.key),
                    "duration": float(note_durations[index]),
                    "offset": float(note_offsets[index]),
                    "measure": measure_index,
                }
            )
        return events

    def _left_hand_events(
        self,
        measure: MeasurePlan,
        texture: str,
        tonic_pc: int,
        mode: str,
        time: dict[str, Any],
    ) -> list[dict[str, Any]]:
        chord = self._chord_pitches(measure.chord, tonic_pc, mode, octave=3, low=36, high=60)
        bass = self._bass_pitch(chord[0])
        total = time["expected_duration"]
        if texture == "arpeggiated":
            pattern = [bass, chord[1], chord[2], chord[1]]
            durations = [1] * total
            pitches = [pattern[index % len(pattern)] for index in range(len(durations))]
            return [self._event([pitch], duration, 2, 2, offset) for pitch, (offset, duration) in zip(pitches, self._offsets(durations), strict=False)]
        if texture == "simple_counterpoint":
            durations = self._melody_durations(
                time,
                measure.cadence,
                texture,
                getattr(measure, "rhythmic_density", measure.density),
                measure.index,
            )
            contour = [chord[2], chord[1], chord[0], bass]
            pitches = [self._bass_pitch(contour[index % len(contour)]) for index in range(len(durations))]
            return [self._event([pitch], duration, 2, 2, offset) for pitch, (offset, duration) in zip(pitches, self._offsets(durations), strict=False)]
        if texture == "chordal":
            durations = [total // 2, total - (total // 2)]
            compact = [self._bass_pitch(note) for note in chord[:3]]
            return [self._event(compact, duration, 2, 2, offset) for offset, duration in self._offsets(durations)]
        durations = [total // 2, total - (total // 2)]
        pitches = [bass, self._bass_pitch(chord[1])]
        return [self._event([pitch], duration, 2, 2, offset) for pitch, (offset, duration) in zip(pitches, self._offsets(durations), strict=False)]

    @staticmethod
    def _event(pitches: list[int], duration: int, voice: int, staff: int, offset: int, rest: bool = False, dynamic: str = "mf") -> dict[str, Any]:
        return {"pitches": pitches, "duration": duration, "voice": voice, "staff": staff, "offset": offset, "rest": rest, "dynamic": dynamic}

    def _left_hand_events_from_accompaniment(self, accompaniment_measure: dict[str, Any], time: dict[str, Any]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for item in accompaniment_measure.get("events", []):
            duration = max(1, int(round(float(item.get("duration_quarters", 1.0)) * time["divisions"])))
            offset = max(0, int(round(float(item.get("offset_quarters", 0.0)) * time["divisions"])))
            pitches = [self._pitch_name_to_midi(str(pitch)) for pitch in item.get("pitches", [])]
            events.append(self._event(pitches, duration, 2, 2, offset, dynamic="mp"))
        return events

    @staticmethod
    def _offsets(durations: list[int]) -> list[tuple[int, int]]:
        offset = 0
        pairs = []
        for duration in durations:
            pairs.append((offset, duration))
            offset += duration
        return pairs

    @staticmethod
    def _assign_internal_beams(events: list[dict[str, Any]], meter: str, time: dict[str, Any]) -> None:
        group_span = 1.5 if meter == "6/8" else 1.0
        divisions = int(time["divisions"])
        by_group: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
        for event in events:
            event.pop("beam", None)
            if event.get("rest") or int(event.get("duration", 0)) > 2:
                continue
            offset_quarters = int(event.get("offset", 0)) / divisions
            group_index = int(offset_quarters / group_span)
            by_group.setdefault((int(event.get("staff", 1)), int(event.get("voice", 1)), group_index), []).append(event)
        for group in by_group.values():
            ordered = sorted(group, key=lambda item: int(item.get("offset", 0)))
            if len(ordered) < 2:
                continue
            for index, event in enumerate(ordered):
                value = "begin" if index == 0 else "end" if index == len(ordered) - 1 else "continue"
                event["beam"] = {"number": 1, "value": value}

    def _repair_vertical_augmented_collisions(
        self,
        right_events: list[dict[str, Any]],
        left_events: list[dict[str, Any]],
        key: str,
        mode: str,
        measure_index: int,
    ) -> dict[str, Any]:
        repairs: list[dict[str, Any]] = []
        if not right_events or not left_events:
            return {"measure": measure_index, "repair_count": 0, "repairs": repairs}
        for _pass in range(4):
            collision = self._first_vertical_augmented_collision(right_events, left_events, key)
            if not collision:
                break
            target = collision["right"]
            event = target["event"]
            pitch_index = int(target["pitch_index"])
            original = int(event["pitches"][pitch_index])
            context = [int(item["midi"]) for item in collision["sounding"] if item["event"] is not event]
            replacement = self._nearest_non_colliding_pitch(original, context, key, mode)
            if replacement == original:
                break
            event["pitches"][pitch_index] = replacement
            repairs.append(
                {
                    "measure": measure_index,
                    "offset": int(event.get("offset", 0) or 0),
                    "from": self._pitch_name(original, key),
                    "to": self._pitch_name(replacement, key),
                    "reason": "augmented_unison_or_octave_vertical_collision",
                }
            )
        return {"measure": measure_index, "repair_count": len(repairs), "repairs": repairs}

    def _align_minor_harmony_and_melody(
        self,
        right_events: list[dict[str, Any]],
        left_events: list[dict[str, Any]],
        chord_symbol: str,
        tonic_pc: int,
        mode: str,
        key: str,
        measure_index: int,
    ) -> dict[str, Any]:
        repairs: list[dict[str, Any]] = []
        if mode != "minor":
            return {"measure": measure_index, "repair_count": 0, "repairs": repairs}

        clean = self._clean_roman_symbol(chord_symbol)
        lowered_third_repairs = self._repair_minor_left_hand_quality(left_events, clean, tonic_pc, key)
        repairs.extend(lowered_third_repairs)

        # If the lower staff uses functional dominant harmony in a minor key,
        # the melodic layer should use the raised leading tone in that measure.
        # Otherwise the visible result reads as natural-minor melody over a
        # harmonic-minor dominant, which is the "upper minor / lower major"
        # mismatch reported by users.
        if clean in {"V", "V7"} or clean.startswith("V/"):
            natural_seventh = (int(tonic_pc) + 10) % 12
            raised_leading = (int(tonic_pc) + 11) % 12
            for event in right_events:
                if event.get("rest"):
                    continue
                for index, midi in enumerate(list(event.get("pitches", []))):
                    midi = int(midi)
                    if midi % 12 != natural_seventh:
                        continue
                    replacement = self._nearest_pitch_class_in_register(midi, raised_leading)
                    event["pitches"][index] = replacement
                    repairs.append(
                        {
                            "measure": measure_index,
                            "offset": int(event.get("offset", 0) or 0),
                            "from": self._pitch_name(midi, key),
                            "to": self._pitch_name(replacement, key),
                            "reason": "minor_dominant_requires_raised_leading_tone",
                        }
                    )
        return {"measure": measure_index, "repair_count": len(repairs), "repairs": repairs}

    def _repair_minor_left_hand_quality(
        self,
        left_events: list[dict[str, Any]],
        clean_chord: str,
        tonic_pc: int,
        key: str,
    ) -> list[dict[str, Any]]:
        repairs: list[dict[str, Any]] = []
        pc_rewrites: dict[int, int] = {}
        if clean_chord in {"I", "i"}:
            pc_rewrites[(tonic_pc + 4) % 12] = (tonic_pc + 3) % 12
        elif clean_chord in {"IV", "iv"}:
            pc_rewrites[(tonic_pc + 9) % 12] = (tonic_pc + 8) % 12
        elif clean_chord == "ii":
            pc_rewrites[(tonic_pc + 9) % 12] = (tonic_pc + 8) % 12
        if not pc_rewrites:
            return repairs
        for event in left_events:
            if event.get("rest"):
                continue
            for index, midi in enumerate(list(event.get("pitches", []))):
                midi = int(midi)
                target_pc = pc_rewrites.get(midi % 12)
                if target_pc is None:
                    continue
                replacement = self._nearest_pitch_class_in_register(midi, target_pc)
                event["pitches"][index] = replacement
                repairs.append(
                    {
                        "offset": int(event.get("offset", 0) or 0),
                        "from": self._pitch_name(midi, key),
                        "to": self._pitch_name(replacement, key),
                        "reason": "minor_left_hand_chord_quality_alignment",
                    }
                )
        return repairs

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
    def _nearest_pitch_class_in_register(midi: int, target_pc: int) -> int:
        candidates = []
        for octave in range(1, 8):
            candidate = (octave + 1) * 12 + int(target_pc) % 12
            candidates.append(candidate)
        return int(min(candidates, key=lambda item: (abs(item - int(midi)), item)))

    def _first_vertical_augmented_collision(
        self,
        right_events: list[dict[str, Any]],
        left_events: list[dict[str, Any]],
        key: str,
    ) -> dict[str, Any] | None:
        flattened = self._flatten_vertical_events(right_events + left_events, key)
        times = sorted({int(item["start"]) for item in flattened} | {int(item["end"]) for item in flattened})
        for time in times:
            sounding = [item for item in flattened if int(item["start"]) <= time < int(item["end"])]
            for left_index, left in enumerate(sounding):
                for right in sounding[left_index + 1 :]:
                    if int(left["staff"]) == int(right["staff"]) and int(left["voice"]) == int(right["voice"]):
                        continue
                    if not self._is_augmented_unison_or_octave(left["midi"], right["midi"], key):
                        continue
                    right_item = left if int(left["staff"]) == 1 else right if int(right["staff"]) == 1 else right
                    return {"right": right_item, "left": right if right_item is left else left, "sounding": sounding, "time": time}
        return None

    @staticmethod
    def _flatten_vertical_events(events: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        flattened: list[dict[str, Any]] = []
        for event in events:
            if event.get("rest"):
                continue
            start = int(event.get("offset", 0) or 0)
            end = start + int(event.get("duration", 0) or 0)
            for pitch_index, midi in enumerate(event.get("pitches", [])):
                flattened.append(
                    {
                        "event": event,
                        "pitch_index": pitch_index,
                        "midi": int(midi),
                        "staff": int(event.get("staff", 1) or 1),
                        "voice": int(event.get("voice", 1) or 1),
                        "start": start,
                        "end": end,
                        "pitch_name": RuleBasedGenerator._pitch_name(int(midi), key),
                    }
                )
        return flattened

    @staticmethod
    def _is_augmented_unison_or_octave(first_midi: int, second_midi: int, key: str) -> bool:
        first = RuleBasedGenerator._spelled_pitch_info(first_midi, key)
        second = RuleBasedGenerator._spelled_pitch_info(second_midi, key)
        lower, upper = (first, second) if first["midi"] <= second["midi"] else (second, first)
        return (upper["letter"] - lower["letter"]) % 7 == 0 and (upper["midi"] - lower["midi"]) % 12 == 1

    @staticmethod
    def _spelled_pitch_info(midi: int, key: str) -> dict[str, int]:
        pitch = RuleBasedGenerator._pitch_name(int(midi), key)
        step, _alter, octave = RuleBasedGenerator._parse_pitch_name(pitch)
        return {"midi": int(midi), "letter": {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}.get(step, 0) + 7 * octave}

    @staticmethod
    def _nearest_non_colliding_pitch(original: int, context: list[int], key: str, mode: str) -> int:
        allowed = RuleBasedGenerator._allowed_melodic_pitch_classes(key, mode)
        candidates = [original + delta for delta in (1, -1, 2, -2, 3, -3, 4, -4)]
        candidates = [item for item in candidates if 48 <= item <= 88]
        candidates.sort(key=lambda item: (0 if item % 12 in allowed else 1, abs(item - original), item))
        for candidate in candidates:
            if any(RuleBasedGenerator._is_augmented_unison_or_octave(candidate, other, key) for other in context):
                continue
            return int(candidate)
        return int(original)

    @staticmethod
    def _allowed_melodic_pitch_classes(key: str, mode: str) -> set[int]:
        tonic = RuleBasedGenerator._tonic(key)
        tonic_pc = RuleBasedGenerator._tonic_pc(tonic)
        major = [0, 2, 4, 5, 7, 9, 11]
        minor_with_leading = [0, 2, 3, 5, 7, 8, 10, 11]
        scale = minor_with_leading if mode == "minor" else major
        return {(tonic_pc + item) % 12 for item in scale}

    @staticmethod
    def _melody_durations(
        time: dict[str, Any],
        cadence: str,
        texture: str,
        density: str = "medium",
        measure_index: int = 1,
    ) -> list[int]:
        total = time["expected_duration"]
        if cadence in {"authentic", "half", "authentic cadence", "half cadence"}:
            if total >= 8 and cadence in {"authentic", "authentic cadence"}:
                return [2, 2, 4]
            return [total // 2, total - (total // 2)]
        if time["beat_type"] == 8:
            if density == "high" or texture in {"arpeggiated", "simple_counterpoint"}:
                return [1] * total
            if density == "medium":
                return [1, 1, 2, 2] if total == 6 else [1] * total
            return [3, 3]
        if time["beats"] == 3:
            if density == "high":
                return [1, 1, 1, 1, 2]
            if density == "medium":
                return [2, 1, 1, 2] if measure_index % 2 else [1, 1, 2, 2]
            return [4, 2]
        if texture == "arpeggiated":
            return [1, 1, 2, 1, 1, 2] if density != "low" else [2, 2, 2, 2]
        if density == "high":
            patterns = [[1, 1, 1, 1, 2, 2], [1, 1, 2, 1, 1, 2], [2, 1, 1, 1, 1, 2]]
            return patterns[(measure_index - 1) % len(patterns)]
        if density == "low":
            return [4, 4] if measure_index % 2 else [6, 2]
        patterns = [[1, 1, 2, 2, 2], [2, 1, 1, 2, 2], [3, 1, 2, 2], [2, 2, 1, 1, 2]]
        return patterns[(measure_index - 1) % len(patterns)]

    @staticmethod
    def _melody_pitches(
        degree_hints: list[str],
        tonic_pc: int,
        mode: str,
        count: int,
        cadence: str,
        contour: str = "wave",
        interval_profile: str = "mixed",
    ) -> list[int]:
        if contour == "style_locked":
            cadence = "none"
        if cadence in {"authentic", "authentic cadence"}:
            degree_hints = ["5", "7", "1"]
        elif cadence in {"half", "half cadence"}:
            degree_hints = ["2", "4", "5"]
        hints = list(degree_hints or RuleBasedGenerator._contour_degrees(contour, interval_profile, mode))
        if interval_profile == "leaping" and cadence in {"none", ""}:
            hints = ["1", "5", "3", "6", "4", "7"]
        elif contour in {"ascending", "descending", "arch", "wave", "static"}:
            hints = RuleBasedGenerator._merge_degree_hints(
                hints,
                RuleBasedGenerator._contour_degrees(contour, interval_profile, mode),
            )
        while len(hints) < count:
            hints.extend(hints)
        hints = hints[:count]
        degree_map = MINOR_DEGREES if mode == "minor" else MAJOR_DEGREES
        pitches: list[int] = []
        for pos, degree in enumerate(hints):
            semitone = degree_map.get(degree, 0)
            midi_number = 60 + tonic_pc + semitone
            if pos >= count - 2 and cadence not in {"none", ""}:
                midi_number = 60 + tonic_pc + (7 if degree == "5" else 0)
            while midi_number > 81:
                midi_number -= 12
            while midi_number < 55:
                midi_number += 12
            pitches.append(midi_number)
        return pitches

    @staticmethod
    def _contour_degrees(contour: str, interval_profile: str, mode: str) -> list[str]:
        third = "b3" if mode == "minor" else "3"
        sixth = "b6" if mode == "minor" else "6"
        if contour == "ascending":
            return ["1", "2", third, "5", sixth]
        if contour == "descending":
            return [sixth, "5", third, "2", "1"]
        if contour == "arch":
            return ["1", third, "5", sixth, "5", third]
        if contour == "static":
            return [third, third, "2", third]
        if interval_profile == "leaping":
            return ["1", "5", third, sixth, "4", "2"]
        return ["1", third, "2", "5", "4", sixth]

    @staticmethod
    def _merge_degree_hints(primary: list[str], contour: list[str]) -> list[str]:
        merged: list[str] = []
        for index in range(max(len(primary), len(contour))):
            source = contour if index % 2 else primary
            if index < len(source):
                merged.append(source[index])
            elif index < len(primary):
                merged.append(primary[index])
            elif index < len(contour):
                merged.append(contour[index])
        return merged or contour

    @staticmethod
    def _chord_pitches(chord: str, tonic_pc: int, mode: str, octave: int, low: int, high: int) -> list[int]:
        clean = chord.replace("maj7", "").replace("7", "").replace("°", "")
        major = {
            "I": [0, 4, 7],
            "ii": [2, 5, 9],
            "iii": [4, 7, 11],
            "IV": [5, 9, 12],
            "V": [7, 11, 14],
            "vi": [9, 12, 16],
            "VI": [9, 12, 16],
        }
        minor = {
            "i": [0, 3, 7],
            "ii": [2, 5, 8],
            "III": [3, 7, 10],
            "iv": [5, 8, 12],
            "V": [7, 11, 14],
            "v": [7, 10, 14],
            "VI": [8, 12, 15],
            "VII": [10, 14, 17],
        }
        degrees = (minor if mode == "minor" else major).get(clean, [0, 4, 7])
        base = 12 * (octave + 1) + tonic_pc
        pitches = [base + degree for degree in degrees]
        normalized: list[int] = []
        for pitch in pitches:
            while pitch > high:
                pitch -= 12
            while pitch < low:
                pitch += 12
            normalized.append(pitch)
        return sorted(normalized)

    @staticmethod
    def _bass_pitch(pitch: int) -> int:
        while pitch > 52:
            pitch -= 12
        while pitch < 36:
            pitch += 12
        return pitch

    def _measure_xml(
        self,
        measure: MeasurePlan,
        right_events: list[dict[str, Any]],
        left_events: list[dict[str, Any]],
        key: str,
        time: dict[str, Any],
        first_measure: bool,
        two_staff: bool,
    ) -> str:
        attributes = self._attributes_xml(key, time, two_staff) if first_measure else ""
        direction = (
            f"        <direction placement=\"above\"><direction-type><words>"
            f"{escape(measure.section)} {escape(measure.chord)}"
            f"</words></direction-type></direction>"
        )
        parts = [f'      <measure number="{measure.index}">', attributes, direction]
        for event in right_events:
            parts.extend(self._note_group_xml(event, key))
        if left_events:
            parts.append("        <backup>")
            parts.append(f"          <duration>{time['expected_duration']}</duration>")
            parts.append("        </backup>")
            for event in left_events:
                parts.extend(self._note_group_xml(event, key))
        parts.append("      </measure>")
        return "\n".join(part for part in parts if part)

    def _note_group_xml(self, event: dict[str, Any], key: str) -> list[str]:
        if event.get("rest"):
            return self._rest_note_xml(int(event["duration"]), int(event["voice"]), int(event["staff"]))
        lines: list[str] = []
        for index, midi_number in enumerate(event["pitches"]):
            lines.extend(
                self._note_xml(
                    note_name=self._pitch_name(midi_number, key),
                    duration=int(event["duration"]),
                    voice=int(event["voice"]),
                    staff=int(event["staff"]),
                    chord=index > 0,
                    beam=event.get("beam") if index == 0 else None,
                )
            )
        return lines

    def _events_to_midi_payload(
        self,
        events: list[dict[str, Any]],
        measure_index: int,
        cursor_quarters: float,
        time: dict[str, Any],
        key: str,
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for event in events:
            if event.get("rest") or not event.get("pitches"):
                continue
            start = cursor_quarters + (int(event["offset"]) / time["divisions"])
            duration = int(event["duration"]) / time["divisions"]
            for midi_number in event["pitches"]:
                payload.append(
                    {
                        "measure": measure_index,
                        "pitch": self._pitch_name(midi_number, key),
                        "midi": midi_number,
                        "start_quarter": start,
                        "duration_quarter": duration,
                        "velocity": self._dynamic_velocity(str(event.get("dynamic", "mf"))) if event["staff"] == 1 else 58,
                        "voice": event["voice"],
                        "staff": event["staff"],
                    }
                )
        return payload

    @staticmethod
    def _tonic(key: str) -> str:
        token = key.split()[0].replace("-flat", "b")
        if token not in STEP_TO_SEMITONE and token not in {"C#", "F#", "Bb", "Eb", "Ab", "Db"}:
            return "C"
        return token

    @staticmethod
    def _tonic_pc(tonic: str) -> int:
        if len(tonic) == 1:
            return STEP_TO_SEMITONE.get(tonic, 0)
        step = tonic[0]
        accidental = tonic[1:]
        alter = 1 if accidental == "#" else -1 if accidental == "b" else 0
        return (STEP_TO_SEMITONE.get(step, 0) + alter) % 12

    @staticmethod
    def _pitch_name(midi_number: int, key: str = "C major") -> str:
        mode = "minor" if "minor" in str(key).lower() else "major"
        return midi_to_pitch_name(int(midi_number), key, mode)

    @staticmethod
    def _pitch_name_to_midi(note_name: str) -> int:
        step, alter, octave = RuleBasedGenerator._parse_pitch_name(note_name)
        return (octave + 1) * 12 + STEP_TO_SEMITONE.get(step, 0) + alter

    @staticmethod
    def _parse_pitch_name(note_name: str) -> tuple[str, int, int]:
        step = note_name[0]
        alter = 0
        rest = note_name[1:]
        if rest.startswith("#"):
            alter = 1
            rest = rest[1:]
        elif rest.startswith("b"):
            alter = -1
            rest = rest[1:]
        return step, alter, int(rest)

    @staticmethod
    def _duration_type(duration: int) -> tuple[str, int]:
        mapping = {
            1: ("16th", 0),
            2: ("eighth", 0),
            3: ("eighth", 1),
            4: ("quarter", 0),
            6: ("quarter", 1),
            8: ("half", 0),
            12: ("half", 1),
            16: ("whole", 0),
        }
        return mapping.get(duration, ("quarter", 0))

    @classmethod
    def _note_xml(cls, note_name: str, duration: int, voice: int, staff: int, chord: bool = False, beam: dict[str, Any] | None = None) -> list[str]:
        step, alter, octave = cls._parse_pitch_name(note_name)
        note_type, dots = cls._duration_type(duration)
        alter_xml = [f"          <alter>{alter}</alter>"] if alter else []
        accidental_xml = []
        if alter == 1:
            accidental_xml = ["        <accidental>sharp</accidental>"]
        elif alter == -1:
            accidental_xml = ["        <accidental>flat</accidental>"]
        lines = ["        <note>"]
        if chord:
            lines.append("          <chord/>")
        lines.extend(
            [
                "          <pitch>",
                f"          <step>{step}</step>",
                *alter_xml,
                f"          <octave>{octave}</octave>",
                "          </pitch>",
                f"          <duration>{duration}</duration>",
                f"          <voice>{voice}</voice>",
                f"          <type>{note_type}</type>",
            ]
        )
        lines.extend(["          <dot/>"] * dots)
        lines.extend(accidental_xml)
        lines.append(f"          <staff>{staff}</staff>")
        if beam:
            lines.append(f"          <beam number=\"{int(beam.get('number', 1))}\">{escape(str(beam.get('value', 'continue')))}</beam>")
        lines.append("        </note>")
        return lines

    @classmethod
    def _rest_note_xml(cls, duration: int, voice: int, staff: int) -> list[str]:
        note_type, dots = cls._duration_type(duration)
        lines = [
            "        <note>",
            "          <rest/>",
            f"          <duration>{duration}</duration>",
            f"          <voice>{voice}</voice>",
            f"          <type>{note_type}</type>",
        ]
        lines.extend(["          <dot/>"] * dots)
        lines.extend([f"          <staff>{staff}</staff>", "        </note>"])
        return lines

    @staticmethod
    def _dynamic_velocity(dynamic: str) -> int:
        return {"p": 48, "mp": 60, "mf": 76, "f": 92}.get(dynamic, 76)

    @staticmethod
    def _attributes_xml(key: str, time: dict[str, Any], two_staff: bool) -> str:
        fifths = RuleBasedGenerator._key_fifths(key)
        mode = "minor" if "minor" in key.lower() else "major"
        clefs = (
            [
                "          <staves>2</staves>",
                "          <clef number=\"1\">",
                "            <sign>G</sign>",
                "            <line>2</line>",
                "          </clef>",
                "          <clef number=\"2\">",
                "            <sign>F</sign>",
                "            <line>4</line>",
                "          </clef>",
            ]
            if two_staff
            else [
                "          <clef>",
                "            <sign>G</sign>",
                "            <line>2</line>",
                "          </clef>",
            ]
        )
        return "\n".join(
            [
                "        <attributes>",
                f"          <divisions>{time['divisions']}</divisions>",
                "          <key>",
                f"            <fifths>{fifths}</fifths>",
                f"            <mode>{mode}</mode>",
                "          </key>",
                "          <time>",
                f"            <beats>{time['beats']}</beats>",
                f"            <beat-type>{time['beat_type']}</beat-type>",
                "          </time>",
                *clefs,
                "        </attributes>",
            ]
        )

    @staticmethod
    def _key_fifths(key: str) -> int:
        fifths = {
            "C": 0,
            "G": 1,
            "D": 2,
            "A": 3,
            "E": 4,
            "B": 5,
            "F#": 6,
            "F": -1,
            "Bb": -2,
            "Eb": -3,
            "Ab": -4,
            "Db": -5,
        }
        tonic = RuleBasedGenerator._tonic(key)
        value = fifths.get(tonic, 0)
        if "minor" in key.lower():
            return value - 3
        return value

    @staticmethod
    def _abc_note(note_name: str) -> str:
        step, alter, octave = RuleBasedGenerator._parse_pitch_name(note_name)
        prefix = "^" if alter == 1 else "_" if alter == -1 else ""
        if octave >= 5:
            return f"{prefix}{step.lower()}"
        return f"{prefix}{step}"

    @staticmethod
    def _abc_key(key: str) -> str:
        tonic = RuleBasedGenerator._tonic(key)
        return tonic + ("m" if "minor" in key.lower() else "")

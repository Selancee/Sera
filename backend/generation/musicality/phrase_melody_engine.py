"""Phrase-level melody generation for V0.96.2.

This module builds a complete 4-measure phrase or 8-measure period before the
RuleBasedGenerator writes right-hand events. Older per-measure style shapes stay
available in expectation_melody_engine as fallback, but normal generation should
arrive here first.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

from backend.generation.musicality.melody_expectation_validator import validate_melody_expectation
from backend.generation.musicality.motif_memory import (
    create_motif_memory,
    develop_motif,
    remember_motif,
    retrieve_motif,
    summarize_motif_memory,
)
from backend.generation.musicality.phrase_contour import plan_phrase_contour, score_phrase_contour
from backend.generation.musicality.pitch_spelling import midi_to_pitch_name
from backend.generation.musicality.target_tone_planner import plan_target_tones, target_tone_hit_report
from backend.generation.musicality.tension_release import plan_tension_release_curve, score_tension_release


STEP_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
PENTATONIC_SCALE = [0, 2, 4, 7, 9]
STYLE_SEEDS = {
    "jazz": [[4, 3, 2, 4], [4, 7, 10, 9], [2, 4, 7, 10]],
    "pop": [[0, 4, 7], [7, 9, 7], [0, 7, 9]],
    "classical": [[0, 2, 4, 7], [4, 5, 7, 11], [7, 5, 4, 2]],
    "romantic": [[0, 2, 4, 7, 9], [4, 7, 9, 12, 11]],
    "chinese": [[0, 2, 4, 7], [7, 9, 7, 4], [0, 7, 9, 4]],
    "cyberpunk": [[0, 3, 2], [0, 7, 3], [10, 7, 3]],
    "default": [[0, 2, 4, 7]],
}


def generate_period_melody(
    period_plan: dict[str, Any],
    harmony_plan: list[Any],
    rhythm_plan: list[Any],
    style_profile: dict[str, Any],
    melodic_style_profile: dict[str, Any],
    phrase_memory: dict[str, Any],
    rng: Any,
) -> dict[str, Any]:
    """Generate phrase-level melody for an entire score or period."""

    measures = list(period_plan.get("measures") or [])
    if not measures:
        length = max(1, int(period_plan.get("length_measures", len(harmony_plan) or len(rhythm_plan) or 4) or 4))
        measures = [{"measure": number, "cadence": "none"} for number in range(1, length + 1)]
    phrase_length = max(2, int(period_plan.get("phrase_length_measures", 4) or 4))
    memory = dict(phrase_memory or {})
    family = _style_family(style_profile, melodic_style_profile)
    if not memory.get("motifs"):
        memory = create_motif_memory(_seed_motif(family, rng), {**dict(style_profile or {}), **dict(melodic_style_profile or {})})

    all_events: list[dict[str, Any]] = []
    measure_reports: list[dict[str, Any]] = []
    phrase_reports: list[dict[str, Any]] = []
    all_targets: list[dict[str, Any]] = []
    all_contours: list[dict[str, Any]] = []
    all_tension_reports: list[dict[str, Any]] = []

    for phrase_index, start in enumerate(range(0, len(measures), phrase_length)):
        chunk = measures[start : start + phrase_length]
        if not chunk:
            continue
        role = _period_phrase_role(phrase_index, start + len(chunk) >= len(measures))
        chunk_numbers = [_measure_number(item, start + local + 1) for local, item in enumerate(chunk)]
        chunk_harmony = [_at_measure(harmony_plan, number, "I") for number in chunk_numbers]
        chunk_rhythm = [_at_measure(rhythm_plan, number, {}) for number in chunk_numbers]
        phrase = generate_phrase_melody(
            {
                **dict(period_plan or {}),
                "phrase_id": f"phrase_{phrase_index + 1}",
                "phrase_role": role,
                "phrase_index": phrase_index,
                "measures": chunk,
                "measure_numbers": chunk_numbers,
                "length_measures": len(chunk),
            },
            chunk_harmony,
            chunk_rhythm,
            style_profile,
            melodic_style_profile,
            memory,
            rng,
        )
        memory = phrase.get("phrase_memory", memory)
        all_events.extend(phrase.get("melody_events", []))
        measure_reports.extend(phrase.get("measures", []))
        phrase_reports.append(phrase.get("phrase_report", {}))
        all_targets.extend(phrase.get("target_tones", []))
        all_contours.append(phrase.get("phrase_report", {}).get("contour", {}))
        all_tension_reports.append(phrase.get("phrase_report", {}).get("tension_release_report", {}))

    motif_report = summarize_motif_memory(memory, measure_reports)
    target_report = target_tone_hit_report(all_events, all_targets)
    phrase_scores = _aggregate_phrase_scores(phrase_reports, motif_report, target_report)
    return {
        "engine": "phrase_melody_engine_v0962",
        "source": "phrase_melody_engine",
        "hardcoded_shape_fallback_used": False,
        "fallback_reason": None,
        "style_family": family,
        "phrase_length_measures": phrase_length,
        "melody_events": all_events,
        "measures": measure_reports,
        "phrases": phrase_reports,
        "phrase_memory": memory,
        "motif_memory_report": motif_report,
        "phrase_contour_report": {
            "engine": "phrase_contour_v0962",
            "phrases": all_contours,
            "phrase_contour_score": phrase_scores["phrase_contour_score"],
        },
        "target_tone_report": {"targets": all_targets, **target_report},
        "tension_release_report": {
            "engine": "tension_release_v0962",
            "phrases": all_tension_reports,
            "curve_match_score": phrase_scores["tension_release_score"],
        },
        "phrase_level_scores": phrase_scores,
    }


def generate_phrase_melody(
    phrase_plan: dict[str, Any],
    harmony_plan: list[Any],
    rhythm_plan: list[Any],
    style_profile: dict[str, Any],
    melodic_style_profile: dict[str, Any],
    phrase_memory: dict[str, Any],
    rng: Any,
) -> dict[str, Any]:
    """Generate one phrase as final insertable melody events."""

    family = _style_family(style_profile, melodic_style_profile)
    key = str(phrase_plan.get("key") or (style_profile or {}).get("key") or (melodic_style_profile or {}).get("key") or "C major")
    mode = "minor" if "minor" in key.lower() else "major"
    tonic_pc = int(phrase_plan.get("tonic_pc", _key_tonic_pc(key)) or 0)
    root_midi = _root_midi(tonic_pc)
    phrase_role = str(phrase_plan.get("phrase_role") or "antecedent")
    phrase_id = str(phrase_plan.get("phrase_id") or "phrase_1")
    measure_numbers = [int(item) for item in phrase_plan.get("measure_numbers", [])]
    if not measure_numbers:
        measure_numbers = [_measure_number(item, index + 1) for index, item in enumerate(phrase_plan.get("measures", []) or [])]
    if not measure_numbers:
        measure_numbers = list(range(1, max(1, int(phrase_plan.get("length_measures", 4) or 4)) + 1))

    memory = dict(phrase_memory or {})
    if not memory.get("motifs"):
        memory = create_motif_memory(_seed_motif(family, rng), {**dict(style_profile or {}), **dict(melodic_style_profile or {})})
    source_motif = retrieve_motif(memory, phrase_role, rng)
    seed_motif = [int(item) for item in source_motif.get("motif", [])] or _seed_motif(family, rng)
    contour = plan_phrase_contour(phrase_role, style_profile, melodic_style_profile, len(measure_numbers), rng)
    targets = plan_target_tones(harmony_plan, phrase_role, {**dict(style_profile or {}), "key": key}, melodic_style_profile)
    tension_curve = plan_tension_release_curve(phrase_role, harmony_plan, {}, {**dict(style_profile or {}), "style_family": family}, rng)

    generated_events: list[dict[str, Any]] = []
    measure_reports: list[dict[str, Any]] = []
    measure_motifs: list[dict[str, Any]] = []
    color_counts = {"approach_tone_count": 0, "enclosure_count": 0, "controlled_mutation_count": 0, "neighbor_tone_count": 0}
    previous_midi: int | None = None
    global_note_index = 0
    total_notes = sum(_non_rest_count(_rhythm_for_local(rhythm_plan, index)) for index in range(len(measure_numbers))) or len(measure_numbers) * 4

    for local_index, measure_number in enumerate(measure_numbers):
        rhythm_measure = _rhythm_for_local(rhythm_plan, local_index)
        non_rest_events = _non_rest_rhythm_events(rhythm_measure)
        note_count = max(1, len(non_rest_events))
        strategy = _measure_strategy(family, phrase_role, local_index, len(measure_numbers))
        motif = develop_motif(seed_motif, strategy, {**dict(style_profile or {}), **dict(melodic_style_profile or {})}, rng)
        while len(motif) < note_count:
            motif.extend(motif or [0])
        target = targets[min(local_index, len(targets) - 1)] if targets else {}
        target_pcs = [int(pc) for pc in target.get("preferred_pitch_classes", [])]
        register_shift = int(contour.get("register_points", [0])[min(local_index, len(contour.get("register_points", [0])) - 1)])
        measure_midis: list[int] = []
        for note_index, rhythm_event in enumerate(non_rest_events):
            phrase_position = global_note_index / max(1, total_notes - 1)
            midi = root_midi + int(motif[note_index % len(motif)]) + register_shift
            midi += _intra_measure_contour_shift(contour, note_index, note_count, phrase_position)
            strong_or_goal = _is_strong_or_goal(note_index, note_count, rhythm_event, local_index, len(measure_numbers))
            if strong_or_goal and target_pcs:
                midi = _nearest_pitch_class(midi, target_pcs)
            else:
                midi, color = _apply_style_color(midi, target_pcs, family, note_index, note_count, local_index, rng)
                if color:
                    color_counts[color] = color_counts.get(color, 0) + 1
            midi = _snap_style_pitch(midi, tonic_pc, family, mode)
            midi = _smooth_from_previous(previous_midi, midi)
            midi = _fit_register(midi, family)
            measure_midis.append(midi)
            previous_midi = midi
            global_note_index += 1
        if local_index == len(measure_numbers) - 1 and target_pcs and measure_midis:
            measure_midis[-1] = _nearest_pitch_class(measure_midis[-1], target_pcs)
            measure_midis[-1] = _fit_register(_snap_style_pitch(measure_midis[-1], tonic_pc, family, mode), family)
        if family == "classical" and phrase_role in {"consequent", "final"} and len(measure_midis) >= 2:
            measure_midis[-2] = _nearest_pitch_class(measure_midis[-2], [(tonic_pc + 11) % 12])
            measure_midis[-1] = _nearest_pitch_class(measure_midis[-1], [tonic_pc])
        generated_measure_events = _events_for_measure(measure_midis, non_rest_events, measure_number, local_index == len(measure_numbers) - 1, key, mode)
        generated_events.extend(generated_measure_events)
        measure_report = {
            "measure": measure_number,
            "phrase_id": phrase_id,
            "phrase_role": phrase_role,
            "phrase_end": local_index == len(measure_numbers) - 1,
            "call_response_role": _call_response_role(phrase_role, local_index),
            "motif_transform": strategy,
            "motif": motif[:note_count],
            "midis": measure_midis,
            "degrees": [_degree_label(midi, tonic_pc, mode) for midi in measure_midis],
            "target_tones": target,
            "contour_type": contour.get("contour_type", ""),
            "tension": (contour.get("tension_curve") or [0.0])[min(local_index, len(contour.get("tension_curve") or [0.0]) - 1)],
        }
        measure_reports.append(measure_report)
        measure_motifs.append(measure_report)
        memory = remember_motif(
            memory,
            f"{phrase_id}_m{measure_number}",
            motif[: max(1, min(len(motif), 4))],
            {"role": phrase_role, "strategy": strategy, "measure": measure_number},
        )

    generated_events = _repair_phrase_line(generated_events, family, tonic_pc, mode, phrase_role, key)
    _sync_measure_reports_from_events(measure_reports, generated_events, tonic_pc, mode)
    expectation = validate_melody_expectation(generated_events, harmony_context=harmony_plan, key=key, style_profile={**dict(style_profile or {}), **dict(melodic_style_profile or {})})
    contour_score = score_phrase_contour(generated_events, contour)
    tension_report = score_tension_release(generated_events, harmony_plan, tension_curve)
    target_report = target_tone_hit_report(generated_events, targets)
    style_report = _style_phrase_report(family, generated_events, measure_reports, target_report, color_counts, tonic_pc)
    phrase_scores = _phrase_scores(contour_score, tension_report, target_report, style_report, measure_reports)
    phrase_report = {
        "phrase_id": phrase_id,
        "phrase_length_measures": len(measure_numbers),
        "phrase_role": phrase_role,
        "motif_id": str(source_motif.get("motif_id", "primary")),
        "contour_type": contour.get("contour_type", ""),
        "tension_curve": contour.get("tension_curve", []),
        "target_tones": targets,
        "cadence_preparation": _cadence_preparation_report(generated_events, target_report, phrase_role),
        "call_response_role": "answer" if phrase_role in {"consequent", "final"} else "call",
        "repairs_applied": [],
        "contour": contour,
        "melody_expectation_report": expectation,
        "target_tone_report": target_report,
        "tension_release_report": tension_report,
        "phrase_level_scores": phrase_scores,
        f"{family}_phrase_report": style_report,
    }
    return {
        "engine": "phrase_melody_engine_v0962",
        "source": "phrase_melody_engine",
        "melody_events": generated_events,
        "phrase_report": phrase_report,
        "measures": measure_reports,
        "target_tones": targets,
        "motif_memory_report": summarize_motif_memory(memory, measure_motifs),
        "phrase_memory": memory,
        "hardcoded_shape_fallback_used": False,
        "fallback_reason": None,
    }


def _aggregate_phrase_scores(phrase_reports: list[dict[str, Any]], motif_report: dict[str, Any], target_report: dict[str, Any]) -> dict[str, float]:
    phrase_scores = [dict(item.get("phrase_level_scores") or {}) for item in phrase_reports]
    keys = [
        "phrase_contour_score",
        "motif_development_score",
        "tension_release_score",
        "target_tone_hit_score",
        "cadence_preparation_score",
        "accompaniment_interaction_score",
        "mechanical_template_penalty",
        "style_phrase_match_score",
        "final_score_musicality_proxy",
    ]
    out: dict[str, float] = {}
    for key in keys:
        values = [float(item.get(key, 0.0) or 0.0) for item in phrase_scores]
        out[key] = round(mean(values), 4) if values else 0.0
    out["motif_development_score"] = max(
        out.get("motif_development_score", 0.0),
        min(1.0, float(motif_report.get("developed_repetition_count", 0) or 0) / max(1, float(motif_report.get("motif_recurrence_count", 1) or 1))),
    )
    out["mechanical_template_penalty"] = max(out.get("mechanical_template_penalty", 0.0), float(motif_report.get("mechanical_repetition_penalty", 0.0) or 0.0))
    out["target_tone_hit_score"] = max(out.get("target_tone_hit_score", 0.0), float(target_report.get("target_tone_hit_rate", 0.0) or 0.0))
    out["final_score_musicality_proxy"] = round(
        mean(
            [
                out.get("phrase_contour_score", 0.0),
                out.get("motif_development_score", 0.0),
                out.get("tension_release_score", 0.0),
                out.get("target_tone_hit_score", 0.0),
                out.get("cadence_preparation_score", 0.0),
                out.get("style_phrase_match_score", 0.0),
                max(0.0, 1.0 - out.get("mechanical_template_penalty", 0.0)),
            ]
        ),
        4,
    )
    return out


def _phrase_scores(
    contour_score: dict[str, float],
    tension_report: dict[str, Any],
    target_report: dict[str, Any],
    style_report: dict[str, Any],
    measure_reports: list[dict[str, Any]],
) -> dict[str, float]:
    motif_development = _motif_development_score(measure_reports)
    mechanical_penalty = _mechanical_penalty(measure_reports)
    cadence_score = mean(
        [
            float(target_report.get("required_target_tone_hit_rate", 0.0) or 0.0),
            float(tension_report.get("cadence_release_score", 0.0) or 0.0),
        ]
    )
    style_score = float(style_report.get("style_phrase_match_score", style_report.get("singability_score", 0.75)) or 0.75)
    scores = {
        "phrase_contour_score": float(contour_score.get("phrase_contour_score", 0.0) or 0.0),
        "motif_development_score": motif_development,
        "tension_release_score": float(tension_report.get("curve_match_score", 0.0) or 0.0),
        "target_tone_hit_score": float(target_report.get("target_tone_hit_rate", 0.0) or 0.0),
        "cadence_preparation_score": cadence_score,
        "accompaniment_interaction_score": 0.65,
        "mechanical_template_penalty": mechanical_penalty,
        "style_phrase_match_score": style_score,
    }
    scores["final_score_musicality_proxy"] = mean(
        [
            scores["phrase_contour_score"],
            scores["motif_development_score"],
            scores["tension_release_score"],
            scores["target_tone_hit_score"],
            scores["cadence_preparation_score"],
            scores["style_phrase_match_score"],
            max(0.0, 1.0 - scores["mechanical_template_penalty"]),
        ]
    )
    return {key: round(float(value), 4) for key, value in scores.items()}


def _style_phrase_report(
    family: str,
    events: list[dict[str, Any]],
    measures: list[dict[str, Any]],
    target_report: dict[str, Any],
    color_counts: dict[str, int],
    tonic_pc: int,
) -> dict[str, Any]:
    midis = [int(item.get("midi", 60) or 60) for item in events if item.get("midi") is not None]
    pcs = [midi % 12 for midi in midis]
    if family == "jazz":
        guide_hit = float(target_report.get("target_tone_hit_rate", 0.0) or 0.0)
        return {
            "guide_tone_hit_rate": round(guide_hit, 4),
            "approach_tone_count": int(color_counts.get("approach_tone_count", 0)),
            "enclosure_count": int(color_counts.get("enclosure_count", 0)),
            "chromatic_resolution_rate": 1.0 if int(color_counts.get("approach_tone_count", 0)) else 0.75,
            "style_phrase_match_score": round(mean([guide_hit, 1.0 if color_counts.get("approach_tone_count", 0) else 0.65]), 4),
        }
    if family == "pop":
        fingerprints = [_interval_fingerprint(item.get("midis", [])) for item in measures if item.get("midis")]
        repeated = len(fingerprints) - len(set(fingerprints))
        singability = _singability_score(midis)
        return {
            "hook_cell": measures[0].get("degrees", [])[:3] if measures else [],
            "hook_repetition_count": max(0, repeated),
            "hook_variation_count": max(0, len(fingerprints) - repeated - 1),
            "singability_score": singability,
            "stable_tone_arrival_rate": float(target_report.get("target_tone_hit_rate", 0.0) or 0.0),
            "style_phrase_match_score": round(mean([singability, min(1.0, (repeated + 1) / max(1, len(fingerprints)))]), 4),
        }
    if family == "classical":
        cadence = float(target_report.get("required_target_tone_hit_rate", 0.0) or 0.0)
        return {
            "antecedent_consequent_score": 0.85,
            "period_balance_score": 1.0 if len(measures) in {2, 4, 8} else 0.7,
            "leading_tone_resolution_rate": cadence,
            "cadence_preparation_score": cadence,
            "style_phrase_match_score": round(mean([0.85, cadence]), 4),
        }
    if family == "romantic":
        line_range = (max(midis) - min(midis)) if midis else 0
        return {
            "long_line_score": min(1.0, len(midis) / 18),
            "delayed_resolution_count": int(color_counts.get("neighbor_tone_count", 0)),
            "neighbor_tone_count": int(color_counts.get("neighbor_tone_count", 0)),
            "phrase_arc_score": min(1.0, line_range / 14),
            "style_phrase_match_score": round(mean([min(1.0, len(midis) / 18), min(1.0, line_range / 14)]), 4),
        }
    if family == "chinese":
        pentatonic = {(tonic_pc + item) % 12 for item in PENTATONIC_SCALE}
        rate = sum(1 for pc in pcs if pc in pentatonic) / max(1, len(pcs))
        center = sum(1 for pc in pcs[-4:] if pc in {tonic_pc, (tonic_pc + 7) % 12}) / max(1, min(4, len(pcs)))
        return {
            "pentatonic_note_rate": round(rate, 4),
            "modal_center_arrival_rate": round(center, 4),
            "open_space_contour_score": 0.85,
            "excess_leading_tone_penalty": 0.0,
            "style_phrase_match_score": round(mean([rate, center, 0.85]), 4),
        }
    if family == "cyberpunk":
        fingerprints = [_interval_fingerprint(item.get("midis", [])[:3]) for item in measures if item.get("midis")]
        repeated = len(fingerprints) - len(set(fingerprints))
        modal = {(tonic_pc + item) % 12 for item in MINOR_SCALE}
        modal_rate = sum(1 for pc in pcs if pc in modal) / max(1, len(pcs))
        return {
            "short_cell_repetition_score": min(1.0, (repeated + 1) / max(1, len(fingerprints))),
            "ostinato_tension_score": 0.8,
            "modal_pitch_rate": round(modal_rate, 4),
            "controlled_mutation_count": int(color_counts.get("controlled_mutation_count", 0)),
            "style_phrase_match_score": round(mean([modal_rate, 0.8]), 4),
        }
    return {"style_phrase_match_score": 0.75}


def _cadence_preparation_report(events: list[dict[str, Any]], target_report: dict[str, Any], phrase_role: str) -> dict[str, Any]:
    last = next((event for event in reversed(events) if event.get("midi") is not None), {})
    return {
        "phrase_role": phrase_role,
        "final_pitch": int(last.get("midi", 0) or 0),
        "target_hit": float(target_report.get("required_target_tone_hit_rate", 0.0) or 0.0) >= 0.7,
        "cadence_preparation_score": float(target_report.get("required_target_tone_hit_rate", 0.0) or 0.0),
    }


def _repair_phrase_line(events: list[dict[str, Any]], family: str, tonic_pc: int, mode: str, phrase_role: str, key: str) -> list[dict[str, Any]]:
    repaired = [dict(event) for event in events]
    previous: int | None = None
    for event in repaired:
        if event.get("midi") is None:
            continue
        midi = int(event["midi"])
        midi = _smooth_from_previous(previous, midi)
        midi = _snap_style_pitch(midi, tonic_pc, family, mode)
        midi = _fit_register(midi, family)
        event["midi"] = midi
        event["pitch"] = _pitch_name(midi, key, mode)
        previous = midi
    _expand_range_if_needed(repaired, family, tonic_pc, mode, key)
    _resolve_unprepared_large_leaps(repaired, family, tonic_pc, mode, key)
    if phrase_role in {"consequent", "final", "cadence"} and repaired:
        for event in reversed(repaired):
            if event.get("midi") is None:
                continue
            target = tonic_pc if family != "jazz" else (tonic_pc + 4) % 12
            event["midi"] = _fit_register(_nearest_pitch_class(int(event["midi"]), [target]), family)
            event["pitch"] = _pitch_name(int(event["midi"]), key, mode)
            event["phrase_end"] = True
            break
    _resolve_unprepared_large_leaps(repaired, family, tonic_pc, mode, key)
    return repaired


def _sync_measure_reports_from_events(measure_reports: list[dict[str, Any]], events: list[dict[str, Any]], tonic_pc: int, mode: str) -> None:
    by_measure: dict[int, list[int]] = {}
    for event in events:
        if event.get("midi") is None:
            continue
        by_measure.setdefault(int(event.get("measure", 0) or 0), []).append(int(event["midi"]))
    for report in measure_reports:
        measure = int(report.get("measure", 0) or 0)
        midis = by_measure.get(measure)
        if not midis:
            continue
        report["midis"] = list(midis)
        report["degrees"] = [_degree_label(midi, tonic_pc, mode) for midi in midis]


def _expand_range_if_needed(events: list[dict[str, Any]], family: str, tonic_pc: int, mode: str, key: str) -> None:
    note_indexes = [index for index, event in enumerate(events) if event.get("midi") is not None]
    if len(note_indexes) < 4:
        return
    midis = [int(events[index]["midi"]) for index in note_indexes]
    required = 9 if family == "romantic" else 7
    if max(midis) - min(midis) >= required:
        return
    target_position = note_indexes[min(len(note_indexes) - 2, max(1, int(len(note_indexes) * 0.62)))]
    current = int(events[target_position]["midi"])
    needed = required - (max(midis) - min(midis))
    candidate = _fit_register(_snap_style_pitch(current + max(needed, 2), tonic_pc, family, mode), family)
    if max(candidate, max(midis)) - min(midis) < required:
        candidate = _fit_register(_snap_style_pitch(current + 12, tonic_pc, family, mode), family)
    events[target_position]["midi"] = candidate
    events[target_position]["pitch"] = _pitch_name(candidate, key, mode)


def _resolve_unprepared_large_leaps(events: list[dict[str, Any]], family: str, tonic_pc: int, mode: str, key: str) -> None:
    for index in range(len(events) - 2):
        first = events[index]
        second = events[index + 1]
        third = events[index + 2]
        if first.get("midi") is None or second.get("midi") is None or third.get("midi") is None:
            continue
        if int(first.get("measure", 0) or 0) != int(second.get("measure", 0) or 0):
            continue
        if int(second.get("measure", 0) or 0) != int(third.get("measure", 0) or 0):
            continue
        leap = int(second["midi"]) - int(first["midi"])
        if abs(leap) <= 7:
            continue
        recovery = int(third["midi"]) - int(second["midi"])
        if leap * recovery < 0 and abs(recovery) <= 2:
            continue
        target = _recovery_pitch_after_large_leap(int(second["midi"]), leap, family, tonic_pc, mode)
        third["midi"] = target
        third["pitch"] = _pitch_name(target, key, mode)


def _recovery_pitch_after_large_leap(second_midi: int, leap: int, family: str, tonic_pc: int, mode: str) -> int:
    direction = -1 if leap > 0 else 1
    for step in (1, 2):
        raw = int(second_midi) + direction * step
        snapped = _fit_register(_snap_style_pitch(raw, tonic_pc, family, mode), family)
        recovery = snapped - int(second_midi)
        if leap * recovery < 0 and abs(recovery) <= 2:
            return snapped
    return _fit_register(int(second_midi) + direction, family)


def _measure_strategy(family: str, phrase_role: str, local_index: int, phrase_length: int) -> str:
    if local_index == phrase_length - 1:
        return "cadential_variant"
    if family == "pop":
        return ["repeat", "rhythmic_variation", "answer_phrase", "cadential_variant"][local_index % 4]
    if family == "classical":
        return ["repeat", "sequence_up", "answer_phrase", "cadential_variant"][local_index % 4]
    if family == "romantic":
        return ["interval_expansion", "sequence_up", "rhythmic_variation", "cadential_variant"][local_index % 4]
    if family == "chinese":
        return ["repeat", "sequence_up", "answer_phrase", "cadential_variant"][local_index % 4]
    if family == "cyberpunk":
        return ["repeat", "style_colored_variant", "rhythmic_variation", "cadential_variant"][local_index % 4]
    if family == "jazz":
        return ["style_colored_variant", "sequence_down", "answer_phrase", "cadential_variant"][local_index % 4]
    return ["repeat", "sequence_up", "answer_phrase", "cadential_variant"][local_index % 4]


def _events_for_measure(midis: list[int], rhythm_events: list[dict[str, Any]], measure_number: int, phrase_end: bool, key: str, mode: str) -> list[dict[str, Any]]:
    events = []
    for index, midi in enumerate(midis):
        rhythm = rhythm_events[min(index, len(rhythm_events) - 1)] if rhythm_events else {"duration_quarters": 1.0, "offset_quarters": float(index)}
        events.append(
            {
                "type": "note",
                "midi": int(midi),
                "pitch": _pitch_name(int(midi), key, mode),
                "duration": float(rhythm.get("duration_quarters", 1.0) or 1.0),
                "offset": float(rhythm.get("offset_quarters", 0.0) or 0.0),
                "measure": int(measure_number),
                "phrase_end": bool(phrase_end and index == len(midis) - 1),
            }
        )
    return events


def _non_rest_rhythm_events(rhythm_measure: Any) -> list[dict[str, Any]]:
    events = list((rhythm_measure or {}).get("events", []) if isinstance(rhythm_measure, dict) else [])
    non_rest = [dict(item) for item in events if not item.get("is_rest")]
    if non_rest:
        return non_rest
    return [
        {"duration_quarters": 1.0, "offset_quarters": 0.0},
        {"duration_quarters": 1.0, "offset_quarters": 1.0},
        {"duration_quarters": 1.0, "offset_quarters": 2.0},
        {"duration_quarters": 1.0, "offset_quarters": 3.0},
    ]


def _non_rest_count(rhythm_measure: Any) -> int:
    return len(_non_rest_rhythm_events(rhythm_measure))


def _rhythm_for_local(rhythm_plan: list[Any], local_index: int) -> Any:
    if local_index < len(rhythm_plan):
        return rhythm_plan[local_index]
    return {}


def _apply_style_color(midi: int, target_pcs: list[int], family: str, note_index: int, note_count: int, local_index: int, rng: Any) -> tuple[int, str]:
    if family == "jazz" and target_pcs and note_count >= 4 and note_index in {1, note_count - 2}:
        target = _nearest_pitch_class(midi, target_pcs)
        return target - 1 if note_index % 2 else target + 1, "approach_tone_count"
    if family == "romantic" and note_count >= 4 and note_index == note_count - 2:
        return midi + 2, "neighbor_tone_count"
    if family == "cyberpunk" and note_index == 1 and local_index % 2 == 1:
        return midi - 1, "controlled_mutation_count"
    return midi, ""


def _is_strong_or_goal(note_index: int, note_count: int, rhythm_event: dict[str, Any], local_index: int, phrase_length: int) -> bool:
    offset = float(rhythm_event.get("offset_quarters", 0.0) or 0.0)
    return note_index == 0 or abs(offset - round(offset)) < 0.01 or (local_index == phrase_length - 1 and note_index == note_count - 1)


def _intra_measure_contour_shift(contour: dict[str, Any], note_index: int, note_count: int, phrase_position: float) -> int:
    contour_type = str(contour.get("contour_type", "arch"))
    if note_count <= 1:
        return 0
    local = note_index / max(1, note_count - 1)
    if contour_type in {"arch", "long_romantic_arc", "classical_periodic_balance"}:
        return int(round((1.0 - abs(local - 0.5) * 2.0) * 3))
    if contour_type in {"rising_question", "jazz_guided_line"}:
        return int(round(local * 3))
    if contour_type == "falling_answer":
        return int(round((1.0 - local) * 3))
    if contour_type == "cyberpunk_cell_tension":
        return 1 if (note_index + int(phrase_position * 10)) % 3 == 1 else 0
    return 0


def _snap_style_pitch(midi: int, tonic_pc: int, family: str, mode: str) -> int:
    if family == "jazz":
        return int(midi)
    if family == "chinese":
        return _nearest_pc_in_scale(midi, tonic_pc, PENTATONIC_SCALE)
    if family == "cyberpunk":
        return _nearest_pc_in_scale(midi, tonic_pc, MINOR_SCALE)
    return _nearest_pc_in_scale(midi, tonic_pc, MINOR_SCALE if mode == "minor" else MAJOR_SCALE)


def _nearest_pc_in_scale(midi: int, tonic_pc: int, scale: list[int]) -> int:
    allowed = {(tonic_pc + interval) % 12 for interval in scale}
    if midi % 12 in allowed:
        return int(midi)
    candidates = []
    for delta in range(-6, 7):
        candidate = midi + delta
        if candidate % 12 in allowed:
            candidates.append(candidate)
    return int(min(candidates, key=lambda item: (abs(item - midi), item)) if candidates else midi)


def _smooth_from_previous(previous: int | None, midi: int) -> int:
    if previous is None:
        return int(midi)
    pitch = int(midi)
    while pitch - previous > 9:
        pitch -= 12
    while previous - pitch > 9:
        pitch += 12
    if abs(pitch - previous) == 6:
        pitch += 1 if pitch < previous else -1
    return pitch


def _fit_register(midi: int, family: str) -> int:
    low, high = (57, 82)
    if family == "cyberpunk":
        low, high = (55, 76)
    elif family in {"pop", "romantic"}:
        low, high = (60, 84)
    elif family == "chinese":
        low, high = (57, 81)
    pitch = int(midi)
    while pitch < low:
        pitch += 12
    while pitch > high:
        pitch -= 12
    return pitch


def _nearest_pitch_class(midi: int, pcs: list[int]) -> int:
    if not pcs:
        return int(midi)
    candidates = []
    for octave in range(3, 7):
        for pc in pcs:
            candidates.append((octave + 1) * 12 + (int(pc) % 12))
    return int(min(candidates, key=lambda item: (abs(item - midi), item)))


def _seed_motif(family: str, rng: Any) -> list[int]:
    seeds = STYLE_SEEDS.get(family, STYLE_SEEDS["default"])
    if hasattr(rng, "choice"):
        return [int(item) for item in rng.choice(seeds)]
    return [int(item) for item in seeds[0]]


def _period_phrase_role(phrase_index: int, final_phrase: bool) -> str:
    if final_phrase and phrase_index > 0:
        return "final"
    if phrase_index == 0:
        return "antecedent"
    if phrase_index == 1:
        return "consequent"
    if phrase_index == 2:
        return "contrast"
    return "return"


def _call_response_role(phrase_role: str, local_index: int) -> str:
    if phrase_role in {"consequent", "final"}:
        return "response" if local_index < 3 else "cadence"
    return "call" if local_index < 2 else "continuation"


def _measure_number(item: Any, fallback: int) -> int:
    if isinstance(item, dict):
        return int(item.get("measure", item.get("number", fallback)) or fallback)
    return int(getattr(item, "index", fallback) or fallback)


def _at_measure(items: list[Any], measure_number: int, fallback: Any) -> Any:
    if not items:
        return fallback
    for item in items:
        if isinstance(item, dict) and int(item.get("measure", item.get("number", -1)) or -1) == int(measure_number):
            return item
    index = max(0, min(len(items) - 1, int(measure_number) - 1))
    return items[index]


def _motif_development_score(measures: list[dict[str, Any]]) -> float:
    transforms = {str(item.get("motif_transform", "")) for item in measures if item.get("motif_transform")}
    return round(min(1.0, len(transforms) / 4), 4)


def _mechanical_penalty(measures: list[dict[str, Any]]) -> float:
    fingerprints = [_interval_fingerprint(item.get("midis", [])) for item in measures if item.get("midis")]
    if not fingerprints:
        return 0.0
    repeated = len(fingerprints) - len(set(fingerprints))
    return round(max(0.0, repeated / max(1, len(fingerprints)) - 0.25), 4)


def _interval_fingerprint(midis: list[int]) -> str:
    values = [int(item) for item in midis]
    if len(values) < 2:
        return ""
    return ",".join(str(max(-5, min(5, values[index + 1] - values[index]))) for index in range(len(values) - 1))


def _singability_score(midis: list[int]) -> float:
    if len(midis) < 2:
        return 0.0
    intervals = [abs(midis[index + 1] - midis[index]) for index in range(len(midis) - 1)]
    return round(sum(1 for item in intervals if item <= 7) / max(1, len(intervals)), 4)


def _degree_label(midi: int, tonic_pc: int, mode: str) -> str:
    offsets = {
        0: "1",
        1: "b2",
        2: "2",
        3: "b3",
        4: "3",
        5: "4",
        6: "#4",
        7: "5",
        8: "b6",
        9: "6",
        10: "b7",
        11: "7",
    }
    return offsets.get((int(midi) - int(tonic_pc)) % 12, "1")


def _root_midi(tonic_pc: int) -> int:
    root = 60 + int(tonic_pc)
    while root > 66:
        root -= 12
    while root < 57:
        root += 12
    return root


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
    return (STEP_TO_PC.get(step, 0) + alter) % 12


def _pitch_name(midi: int, key: str = "C major", mode: str | None = None) -> str:
    return midi_to_pitch_name(int(midi), key, mode)


def _style_family(style_profile: dict[str, Any], melodic_style_profile: dict[str, Any]) -> str:
    tags = {str(item).lower() for item in (style_profile or {}).get("custom_style_tags", [])}
    family = str((melodic_style_profile or {}).get("style_family") or (style_profile or {}).get("base_style") or (style_profile or {}).get("style") or "classical").lower()
    if "cyberpunk" in tags or family == "electronic":
        return "cyberpunk"
    if family == "default":
        return "classical"
    return family

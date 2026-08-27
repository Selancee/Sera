"""Deterministic musical and safety critics for composition candidates."""

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from statistics import mean
from typing import Any

from backend.generation.musicality.voice_leading_validator import validate_voice_leading
from backend.generation.musicality.melody_expectation_validator import validate_melody_expectation
from evaluation.analysis.music_statistics import parse_pitch_name
from sera_edit.composer.candidate_generator import chord_pitch_classes, key_context
from sera_edit.composer.models import CompositionPlan
from sera_edit.composer.phrase_analysis import classify_contour
from sera_edit.composer.preference import preference_match_score
from sera_edit.composer.texture_analysis import analyze_texture
from sera_edit.domain.score_scope import EventContext, ScoreScope
from sera_edit.execution.diff_engine import score_diff


def review_candidate(
    before: dict[str, Any],
    after: dict[str, Any],
    plan: CompositionPlan,
    preview: dict[str, Any],
    *,
    style_knowledge: dict[str, Any] | None = None,
    phrase_analysis: dict[str, Any] | None = None,
    preference_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score safety, style, phrase, motif, preference, and playability."""

    # The transaction diff compares the same beam-materialized baseline on both
    # sides. Reuse it here so exporter-derived beam metadata is not mistaken for
    # an agent edit when the source ScoreDocument came directly from MusicXML.
    diff = preview.get("diff") or score_diff(before, after)
    changed_field_counts: dict[str, int] = defaultdict(int)
    for item in diff["changed"]:
        for field in item["changed_fields"]:
            changed_field_counts[str(field)] += 1
    target = ScoreScope.from_dict(plan.target_scope)
    before_contexts = [context for context in target.select(before) if context.event.get("type") == "note"]
    contexts = [context for context in target.select(after) if context.event.get("type") == "note"]
    event_count_preserved = not diff["added"] and not diff["deleted"]
    duration_preserved = all("duration" not in item["changed_fields"] for item in diff["changed"])
    pitch_only = all(set(item["changed_fields"]) <= {"pitch"} for item in diff["changed"])
    transaction_valid = preview.get("validation_report", {}).get("status") in {"valid", "warning"}

    chord_hits = 0
    chord_samples = 0
    by_measure_staff: dict[tuple[int, str], list[tuple[float, int]]] = defaultdict(list)
    by_voice: dict[str, list[tuple[int, float, int]]] = defaultdict(list)
    by_voice_context: dict[str, list[EventContext]] = defaultdict(list)
    for context in contexts:
        midi = parse_pitch_name(str(context.event.get("pitch", "")))
        if midi is None:
            continue
        by_measure_staff[(context.measure, context.staff)].append((float(context.offset), midi))
        by_voice[f"{context.staff}:v{context.voice}"].append((context.measure, float(context.offset), midi))
        by_voice_context[f"{context.staff}:v{context.voice}"].append(context)
        measure_index = plan.measures.index(context.measure) if context.measure in plan.measures else 0
        chord = chord_pitch_classes(plan.harmonic_progression[measure_index % len(plan.harmonic_progression)], plan.key)
        if float(context.offset).is_integer():
            chord_samples += 1
            chord_hits += int(midi % 12 in chord)
    chord_tone_ratio = chord_hits / max(1, chord_samples)

    large_leaps = 0
    for (_, staff), events in by_measure_staff.items():
        ordered = [midi for _, midi in sorted(events)]
        large_leaps += sum(abs(right - left) > 12 for left, right in zip(ordered, ordered[1:], strict=False))

    baseline_range_ids, baseline_crossing_measures = _playability_violations(before_contexts)
    range_ids, crossing_measures = _playability_violations(contexts)
    introduced_range_ids = range_ids - baseline_range_ids
    introduced_crossing_measures = crossing_measures - baseline_crossing_measures
    range_violations = len(range_ids)
    voice_crossings = len(crossing_measures)
    introduced_range_violations = len(introduced_range_ids)
    introduced_voice_crossings = len(introduced_crossing_measures)

    voicings: list[dict[str, Any]] = []
    for measure in plan.measures:
        left = sorted(midi for (_, midi) in by_measure_staff.get((measure, "left_hand"), []))
        right = sorted(midi for (_, midi) in by_measure_staff.get((measure, "right_hand"), []))
        merged = sorted(set(left + right))
        if merged:
            voicings.append({"voicing": merged, "playability_score": 0.0 if range_violations else 1.0})
    voice_leading = validate_voice_leading(
        voicings,
        {
            "style": plan.style_family,
            "allows_parallel_fifths": plan.style_family in {"pop", "minimal", "cinematic"},
        },
    )
    tonic, _ = key_context(plan.key)
    final_midis = [midi for (_, midi) in by_measure_staff.get((plan.measures[-1], "right_hand"), [])]
    cadence_resolved = bool(final_midis and final_midis[-1] % 12 == tonic) or not final_midis

    primary_voice_id = str((phrase_analysis or {}).get("primary_voice_id") or "")
    if primary_voice_id not in by_voice:
        primary_voice_id = next((voice_id for voice_id in sorted(by_voice) if voice_id.startswith("right_hand:")), "")
    if primary_voice_id not in by_voice and by_voice:
        primary_voice_id = max(by_voice, key=lambda voice_id: len(by_voice[voice_id]))
    primary_midis = [midi for _, _, midi in sorted(by_voice.get(primary_voice_id, []))]
    primary_contexts = sorted(
        by_voice_context.get(primary_voice_id, []),
        key=lambda item: (item.measure, item.offset, item.event_id),
    )
    before_by_id = {context.event_id: context for context in before_contexts}
    source_primary_contexts = [before_by_id[item.event_id] for item in primary_contexts if item.event_id in before_by_id]
    expectation_report = validate_melody_expectation(
        [_expectation_event(context) for context in primary_contexts],
        key=plan.key,
        style_profile={"style": plan.style_family},
    )
    source_expectation_report = validate_melody_expectation(
        [_expectation_event(context) for context in source_primary_contexts],
        key=plan.key,
        style_profile={"style": plan.style_family},
    )
    expectation_score = float(expectation_report["melody_expectation_score"])
    source_expectation_score = float(source_expectation_report["melody_expectation_score"])
    expectation_delta = expectation_score - source_expectation_score
    expectation_preservation = max(0.0, min(1.0, 1.0 + min(0.0, expectation_delta) * 2.5))
    source_texture = analyze_texture(before, plan.target_scope)
    candidate_texture = analyze_texture(after, plan.target_scope)
    texture_structure_preserved = all(
        source_texture.get(key) == candidate_texture.get(key)
        for key in ("voice_count", "attack_alignment_ratio", "homorhythmic_similarity")
    )
    style_profile = (style_knowledge or {}).get("profile") or {}
    motif_score = _motif_coherence(primary_midis, phrase_analysis or {}, plan.motif_strategy)
    phrase_score = _phrase_direction_score(by_measure_staff, plan, cadence_resolved)
    style_score = _style_fit_score(primary_midis, plan, style_profile)

    safety_score = mean([float(event_count_preserved), float(duration_preserved), float(pitch_only), float(transaction_valid)])
    theory_score = mean(
        [
            chord_tone_ratio,
            float(cadence_resolved),
            max(0.0, 1.0 - large_leaps / max(1, len(contexts))),
            float(voice_leading["style_harmony_match_score"]),
            expectation_score,
            expectation_preservation,
        ]
    )
    # Host scores may intentionally contain pre-existing register overlaps or
    # unconventional ranges.  A local pitch edit is safe when it introduces no
    # *new* violation; candidates that repair an existing issue should rank
    # above candidates that merely preserve it.
    residual_preexisting = len(range_ids & baseline_range_ids) + len(crossing_measures & baseline_crossing_measures)
    playability_penalty = introduced_range_violations + introduced_voice_crossings + 0.15 * residual_preexisting
    playability_score = max(0.0, 1.0 - playability_penalty / max(1, len(plan.measures)))
    base_review = {
        "motif_score": motif_score,
        "phrase_score": phrase_score,
        "style_score": style_score,
        "theory_score": theory_score,
        "playability_score": playability_score,
    }
    preference_score = preference_match_score(base_review, preference_profile)
    weights = _critic_weights(style_profile, preference_profile)
    overall = sum(
        weights[key] * value
        for key, value in {
            "safety": safety_score,
            "theory": theory_score,
            "playability": playability_score,
            "motif": motif_score,
            "phrase": phrase_score,
            "style": style_score,
            "preference": preference_score,
        }.items()
    )
    hard_valid = (
        transaction_valid
        and event_count_preserved
        and duration_preserved
        and pitch_only
        and introduced_range_violations == 0
        and introduced_voice_crossings == 0
    )
    findings: list[dict[str, Any]] = [
        {"check": "host_scaffold_preserved", "passed": event_count_preserved and duration_preserved and pitch_only, "claim_id": "TH-SAFE-001"},
        {"check": "chord_tone_anchoring", "passed": chord_tone_ratio >= 0.6, "value": round(chord_tone_ratio, 4), "claim_id": "TH-HARM-002"},
        {"check": "cadence_resolution", "passed": cadence_resolved, "claim_id": "TH-HARM-001"},
        {
            "check": "register_playability",
            "passed": introduced_range_violations == 0 and introduced_voice_crossings == 0,
            "value": introduced_range_violations + introduced_voice_crossings,
            "claim_id": "TH-PLAY-001",
        },
        {"check": "voice_leading", "passed": bool(voice_leading["valid"]), "claim_id": "TH-VL-001"},
        {"check": "motif_coherence", "passed": motif_score >= 0.5, "value": round(motif_score, 4), "claim_id": "TH-MOTIF-001"},
        {"check": "phrase_direction", "passed": phrase_score >= 0.5, "value": round(phrase_score, 4), "claim_id": "TH-TENSION-001"},
        {
            "check": "style_profile_match",
            "passed": style_score >= 0.5,
            "value": round(style_score, 4),
            "claim_id": plan.style_rule_ids[0] if plan.style_rule_ids else f"STYLE-{plan.style_family.upper()}-001",
        },
        {
            "check": "melodic_expectation",
            "passed": expectation_score >= 0.62 or expectation_delta >= -0.02,
            "value": round(expectation_score, 4),
            "claim_id": "KB-EXPECT-024",
        },
        {
            "check": "texture_structure_preserved",
            "passed": texture_structure_preserved,
            "value": round(float(texture_structure_preserved), 4),
            "claim_id": "KB-TEXTURE-025",
        },
    ]
    return {
        "status": "valid" if hard_valid else "rejected",
        "overall_score": round(overall, 4),
        "safety_score": round(safety_score, 4),
        "theory_score": round(theory_score, 4),
        "playability_score": round(playability_score, 4),
        "motif_score": round(motif_score, 4),
        "phrase_score": round(phrase_score, 4),
        "style_score": round(style_score, 4),
        "preference_score": round(preference_score, 4),
        "critic_weights": {key: round(value, 4) for key, value in weights.items()},
        "changed_event_count": diff["changed_element_count"],
        "event_count_preserved": event_count_preserved,
        "duration_preserved": duration_preserved,
        "pitch_only": pitch_only,
        "transaction_valid": transaction_valid,
        "changed_field_counts": dict(sorted(changed_field_counts.items())),
        "chord_tone_ratio": round(chord_tone_ratio, 4),
        "large_leap_count": large_leaps,
        "melody_expectation_score": round(expectation_score, 4),
        "source_melody_expectation_score": round(source_expectation_score, 4),
        "melody_expectation_delta": round(expectation_delta, 4),
        "melody_expectation_preservation": round(expectation_preservation, 4),
        "melody_expectation_report": expectation_report,
        "source_texture": source_texture,
        "candidate_texture": candidate_texture,
        "texture_structure_preserved": texture_structure_preserved,
        "range_violation_count": range_violations,
        "voice_crossing_count": voice_crossings,
        "baseline_range_violation_count": len(baseline_range_ids),
        "baseline_voice_crossing_count": len(baseline_crossing_measures),
        "introduced_range_violation_count": introduced_range_violations,
        "introduced_voice_crossing_count": introduced_voice_crossings,
        "cadence_resolved": cadence_resolved,
        "voice_leading": voice_leading,
        "findings": findings,
        "reviewer": "sera_deterministic_critics_v3",
    }


def _expectation_event(context: EventContext) -> dict[str, Any]:
    return {
        "type": "note",
        "pitch": context.event.get("pitch"),
        "duration": context.event.get("duration"),
        "offset": float(context.offset),
        "measure": context.measure,
    }


def _motif_coherence(primary_midis: list[int], phrase_analysis: dict[str, Any], strategy: str) -> float:
    intervals = [right - left for left, right in zip(primary_midis, primary_midis[1:], strict=False)]
    if not intervals:
        return 0.5
    candidate_signs = [_sign(value) for value in intervals]
    source_signs = [int(value) for value in (phrase_analysis.get("source_motif") or {}).get("interval_signs") or []]
    if not source_signs:
        correspondence = 0.5
    else:
        expected = [source_signs[index % len(source_signs)] for index in range(len(candidate_signs))]
        direct = sum(left == right for left, right in zip(candidate_signs, expected, strict=True)) / len(candidate_signs)
        inverse = sum(left == -right for left, right in zip(candidate_signs, expected, strict=True)) / len(candidate_signs)
        correspondence = max(direct, inverse) if strategy in {"inversion_hint", "call_response"} else direct
    cells = [tuple(candidate_signs[index : index + 3]) for index in range(max(0, len(candidate_signs) - 2))]
    repetition = 0.5 if not cells else max(cells.count(cell) for cell in set(cells)) / len(cells)
    return max(0.0, min(1.0, 0.7 * correspondence + 0.3 * repetition))


def _phrase_direction_score(
    by_measure_staff: dict[tuple[int, str], list[tuple[float, int]]],
    plan: CompositionPlan,
    cadence_resolved: bool,
) -> float:
    register = []
    for measure in plan.measures:
        values = [midi for _, midi in by_measure_staff.get((measure, "right_hand"), [])]
        if values:
            register.append(mean(values))
    if len(register) < 2:
        return 0.75 if cadence_resolved else 0.5
    low, high = min(register), max(register)
    normalized = [0.5 for _ in register] if high == low else [(value - low) / (high - low) for value in register]
    tension = list(plan.tension_curve)[: len(normalized)]
    if len(tension) < len(normalized):
        tension.extend([tension[-1] if tension else 0.5] * (len(normalized) - len(tension)))
    curve_fit = 1.0 - mean(abs(left - right) for left, right in zip(normalized, tension, strict=True))
    return max(0.0, min(1.0, 0.75 * curve_fit + 0.25 * float(cadence_resolved)))


def _style_fit_score(primary_midis: list[int], plan: CompositionPlan, style_profile: dict[str, Any]) -> float:
    if len(primary_midis) < 2:
        return 0.5
    intervals = [right - left for left, right in zip(primary_midis, primary_midis[1:], strict=False)]
    step_ratio = sum(abs(interval) <= 2 for interval in intervals) / len(intervals)
    _, scale = key_context(plan.key)
    chromatic_ratio = sum(midi % 12 not in scale for midi in primary_midis) / len(primary_midis)
    melody = style_profile.get("melody") or {}
    step_fit = _range_fit(step_ratio, melody.get("step_ratio_target") or [0.45, 0.9])
    chromatic_fit = _range_fit(chromatic_ratio, melody.get("chromatic_ratio_target") or [0.0, 0.15])
    leap_limit = int(melody.get("leap_limit_semitones") or 12)
    leap_fit = 1.0 - sum(abs(interval) > leap_limit for interval in intervals) / len(intervals)
    contour = classify_contour(primary_midis)
    preferred = list((style_profile.get("planning") or {}).get("preferred_contours") or [])
    contour_fit = 1.0 if not preferred or contour in preferred else 0.45
    return max(0.0, min(1.0, mean([step_fit, chromatic_fit, leap_fit, contour_fit])))


def _range_fit(value: float, target: list[float]) -> float:
    low, high = float(target[0]), float(target[-1])
    if low <= value <= high:
        return 1.0
    distance = low - value if value < low else value - high
    return max(0.0, 1.0 - distance / max(0.15, high - low))


def _critic_weights(style_profile: dict[str, Any], preference_profile: dict[str, Any] | None) -> dict[str, float]:
    weights = dict(
        style_profile.get("critic_weights")
        or {"safety": 0.28, "theory": 0.17, "playability": 0.1, "motif": 0.15, "phrase": 0.14, "style": 0.11, "preference": 0.05}
    )
    feedback_count = int((preference_profile or {}).get("feedback_count") or 0)
    if feedback_count > 0:
        desired = min(0.16, float(weights["preference"]) + 0.02 * sqrt(feedback_count))
        remaining_old = 1.0 - float(weights["preference"])
        scale = (1.0 - desired) / max(1e-9, remaining_old)
        for key in weights:
            if key != "preference":
                weights[key] = float(weights[key]) * scale
        weights["preference"] = desired
    total = sum(float(value) for value in weights.values())
    return {key: float(value) / total for key, value in weights.items()}


def _sign(value: int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _playability_violations(contexts: list[EventContext]) -> tuple[set[str], set[int]]:
    """Return stable event/measure identities for range and hand-crossing issues."""

    range_event_ids: set[str] = set()
    by_measure_staff: dict[tuple[int, str], list[int]] = defaultdict(list)
    for context in contexts:
        midi = parse_pitch_name(str(context.event.get("pitch", "")))
        if midi is None:
            continue
        low, high = ((28, 67) if context.staff == "left_hand" else (45, 88))
        if not low <= midi <= high:
            range_event_ids.add(context.event_id)
        by_measure_staff[(context.measure, context.staff)].append(midi)
    crossing_measures: set[int] = set()
    for measure in {context.measure for context in contexts}:
        left = by_measure_staff.get((measure, "left_hand"), [])
        right = by_measure_staff.get((measure, "right_hand"), [])
        if left and right and max(left) >= min(right):
            crossing_measures.add(measure)
    return range_event_ids, crossing_measures

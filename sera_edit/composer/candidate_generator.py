"""Deterministic note-level realization of a canonical CompositionPlan."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any

from backend.services.score_document_service import normalize_score_document
from backend.generation.musicality.melody_expectation_validator import validate_melody_expectation
from evaluation.analysis.music_statistics import midi_to_pitch, parse_pitch_name
from sera_edit.composer.models import CompositionPlan
from sera_edit.domain.score_scope import EventContext, ScoreScope


STEP_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ROMAN_DEGREES = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6}
MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)


def key_context(key: str) -> tuple[int, tuple[int, ...]]:
    """Return tonic pitch class and diatonic pitch classes for a compact key label."""

    match = re.match(r"^\s*([A-Ga-g])([#b]?)(?:\s+|$)", key)
    if not match:
        tonic = 0
    else:
        step, accidental = match.groups()
        tonic = (STEP_TO_PC[step.upper()] + (1 if accidental == "#" else -1 if accidental == "b" else 0)) % 12
    intervals = MINOR_SCALE if "minor" in key.lower() or re.search(r"\bmin\b", key.lower()) else MAJOR_SCALE
    return tonic, tuple((tonic + interval) % 12 for interval in intervals)


def chord_pitch_classes(symbol: str, key: str) -> tuple[int, int, int]:
    """Resolve a server-allowed Roman symbol to a diatonic triad."""

    tonic, scale = key_context(key)
    del tonic
    clean = re.sub(r"(?:7|o|°)$", "", symbol.strip()).lstrip("b#")
    degree = ROMAN_DEGREES.get(clean.upper(), 0)
    return (scale[degree], scale[(degree + 2) % 7], scale[(degree + 4) % 7])


def generate_candidate_patches(
    score_document: dict[str, Any],
    plan: CompositionPlan,
    *,
    candidate_count: int = 16,
    phrase_analysis: dict[str, Any] | None = None,
    style_knowledge: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate a style-conditioned pool of source-preserving pitch patches."""

    score = normalize_score_document(score_document)
    scope = ScoreScope.from_dict(plan.target_scope)
    protected_scope = ScoreScope.from_dict(plan.protected_scope)
    target_notes = [context for context in scope.select(score) if context.event.get("type") == "note"]
    if not target_notes:
        raise ValueError("当前 Composer 选区没有可重写音高的音符。")
    # Protected events are not useful search candidates: generating operations
    # for them only guarantees an E11 rollback later.  Excluding them here keeps
    # the transaction boundary intact while allowing a partially protected
    # target (for example, both piano staves with the melody protected) to work.
    notes = [context for context in target_notes if not protected_scope.contains(context)]
    if not notes:
        return []
    if plan.mode == "orchestration_advice":
        return []
    staff_bounds = _source_adaptive_staff_bounds(target_notes)
    grouped: dict[tuple[int, str, int], list[EventContext]] = defaultdict(list)
    for context in notes:
        grouped[(context.measure, context.staff, context.voice)].append(context)
    for contexts in grouped.values():
        contexts.sort(key=lambda item: (item.offset, item.event_id))
    style_profile = (style_knowledge or {}).get("profile") or {}
    source_motif = (phrase_analysis or {}).get("source_motif") or {}
    motif_signs = [int(value) for value in source_motif.get("interval_signs") or []]
    primary_voice_id = str((phrase_analysis or {}).get("primary_voice_id") or "")
    result: list[dict[str, Any]] = []
    fingerprints: set[str] = set()
    for variant in range(max(1, min(32, int(candidate_count)))):
        proposed: dict[str, str] = {}
        for (measure, staff, voice), contexts in sorted(grouped.items()):
            voice_id = f"{staff}:v{voice}"
            if plan.mode == "reharmonize" and plan.preserve_melody and voice_id == primary_voice_id:
                continue
            measure_index = plan.measures.index(measure) if measure in plan.measures else 0
            harmony = plan.harmonic_progression[measure_index % len(plan.harmonic_progression)]
            chord = chord_pitch_classes(harmony, plan.key)
            tonic, scale = key_context(plan.key)
            for index, context in enumerate(contexts):
                original = parse_pitch_name(str(context.event.get("pitch", "")))
                if original is None:
                    continue
                if staff == "left_hand":
                    low, high = staff_bounds.get((measure, staff), (28, 67))
                    target_pc = chord[(index + variant + measure_index) % len(chord)]
                    target = _nearest_pitch(original, target_pc, low=low, high=high)
                else:
                    low, high = staff_bounds.get((measure, staff), (45, 88))
                    is_final = measure == plan.measures[-1] and index == len(contexts) - 1
                    if is_final:
                        target_pc = tonic
                    else:
                        target_pc = _melody_pitch_class(
                            original,
                            float(context.offset),
                            index,
                            measure_index,
                            chord,
                            scale,
                            plan.motif_strategy,
                            motif_signs,
                            variant,
                        )
                    contour_bias = _contour_bias(
                        variant,
                        measure_index,
                        len(plan.measures),
                        primary=not primary_voice_id or primary_voice_id == voice_id,
                        preferred_contours=list((style_profile.get("planning") or {}).get("preferred_contours") or []),
                    )
                    target = _nearest_pitch(original + contour_bias, target_pc, low=low, high=high)
                pitch = midi_to_pitch(target)
                if pitch != str(context.event.get("pitch", "")):
                    proposed[context.event_id] = pitch
        if primary_voice_id and not (plan.mode == "reharmonize" and plan.preserve_melody):
            primary_contexts = sorted(
                [
                    context
                    for (_, staff, voice), contexts in grouped.items()
                    if f"{staff}:v{voice}" == primary_voice_id
                    for context in contexts
                ],
                key=lambda item: (item.measure, item.offset, item.event_id),
            )
            proposed = _prefer_expectation_coherent_primary(proposed, primary_contexts, plan)
        if not proposed:
            continue
        identity = hashlib.sha256(json.dumps(proposed, sort_keys=True).encode("utf-8")).hexdigest()
        if identity in fingerprints:
            continue
        fingerprints.add(identity)
        operations = [
            {
                "operation_id": f"{plan.plan_id}_v{variant + 1}_p{position:03d}",
                "type": "set_pitch",
                "selector": {"event_ids": [event_id]},
                "arguments": {"pitch": pitch},
                "preconditions": [{"type": "event_exists", "event_id": event_id}],
                "expected_change_count": 1,
            }
            for position, (event_id, pitch) in enumerate(sorted(proposed.items()), start=1)
        ]
        result.append(
            {
                "schema_version": "1.0.0",
                "patch_id": f"{plan.plan_id}_candidate_{variant + 1}_{identity[:8]}",
                "source_score_id": str(score.get("score_id", "")),
                "source_fingerprint": plan.source_fingerprint,
                "instruction": plan.brief,
                "target_scope": dict(plan.target_scope),
                "protected_scope": dict(plan.protected_scope),
                "preconditions": [],
                "operations": operations,
                "expected_effects": [{"type": "preserve_duration"}],
                "provenance": {
                    "provider": "sera_composer",
                    "model": "deterministic_realizer_v1",
                    "temperature": 0,
                    "seed": plan.seed + variant,
                    "plan_id": plan.plan_id,
                    "theory_claim_ids": list(plan.theory_claim_ids),
                    "style_rule_ids": list(plan.style_rule_ids),
                    "style_knowledge_version": plan.style_knowledge_version,
                    "phrase_fingerprint": (phrase_analysis or {}).get("fingerprint"),
                    "variant": variant + 1,
                },
            }
        )
    return result


def _source_adaptive_staff_bounds(contexts: list[EventContext]) -> dict[tuple[int, str], tuple[int, int]]:
    """Preserve an existing non-crossed hand boundary while realizing new pitches.

    Imported piano scores often use several MusicXML voices on both staves.  A
    fixed left-hand high of 67 and right-hand low of 45 lets every independently
    realized voice cross even when the source hands were separated.  For each
    non-crossed source measure, retain a boundary inside the original gap.  A
    pre-existing crossed measure keeps the wider defaults and is handled by the
    source-relative critic rather than silently being rewritten.
    """

    by_measure_staff: dict[tuple[int, str], list[int]] = defaultdict(list)
    for context in contexts:
        midi = parse_pitch_name(str(context.event.get("pitch", "")))
        if midi is not None:
            by_measure_staff[(context.measure, context.staff)].append(int(midi))
    bounds: dict[tuple[int, str], tuple[int, int]] = {}
    measures = {measure for measure, _ in by_measure_staff}
    for measure in measures:
        left = by_measure_staff.get((measure, "left_hand"), [])
        right = by_measure_staff.get((measure, "right_hand"), [])
        if not left or not right or max(left) >= min(right):
            continue
        boundary = (max(left) + min(right)) // 2
        left_high = max(28, min(67, boundary))
        right_low = min(88, max(45, left_high + 1))
        bounds[(measure, "left_hand")] = (28, left_high)
        bounds[(measure, "right_hand")] = (right_low, 88)
    return bounds


def _prefer_expectation_coherent_primary(
    proposed: dict[str, str],
    contexts: list[EventContext],
    plan: CompositionPlan,
) -> dict[str, str]:
    """Repair avoidable range-expanding leaps while retaining harmony and rhythm."""

    if len(contexts) < 3:
        return proposed
    original_midis = [parse_pitch_name(str(context.event.get("pitch", ""))) for context in contexts]
    if any(value is None for value in original_midis):
        return proposed
    originals = [int(value) for value in original_midis if value is not None]
    candidate = [
        int(parse_pitch_name(proposed.get(context.event_id, str(context.event.get("pitch", "")))) or originals[index])
        for index, context in enumerate(contexts)
    ]
    before_score = _expectation_score(candidate, contexts, plan)
    repaired = list(candidate)
    tonic, scale = key_context(plan.key)
    del tonic
    for index in range(1, len(repaired)):
        context = contexts[index]
        previous = repaired[index - 1]
        current = repaired[index]
        previous_interval = repaired[index - 1] - repaired[index - 2] if index >= 2 else 0
        measure_index = plan.measures.index(context.measure) if context.measure in plan.measures else 0
        chord = chord_pitch_classes(
            plan.harmonic_progression[measure_index % len(plan.harmonic_progression)],
            plan.key,
        )
        strong_position = int(round(float(context.offset) * 2)) % 4 == 0
        allowed_pitch_classes = chord if strong_position else scale
        choices = [midi for midi in range(45, 89) if midi % 12 in allowed_pitch_classes]
        if not choices:
            continue

        def cost(value: int) -> tuple[float, int, int]:
            interval = value - previous
            distance = abs(interval)
            penalty = max(0, distance - 5) * 3.0
            if distance == 6:
                penalty += 4.0
            if abs(previous_interval) > 5:
                reversed_by_step = _sign(interval) != _sign(previous_interval) and distance <= 4
                if not reversed_by_step:
                    penalty += 12.0
            penalty += 0.18 * abs(value - current) + 0.08 * abs(value - originals[index])
            return penalty, abs(value - current), value

        repaired[index] = min(choices, key=cost)
    after_score = _expectation_score(repaired, contexts, plan)
    if after_score <= before_score + 0.005:
        return proposed
    result = dict(proposed)
    for context, original, midi in zip(contexts, originals, repaired, strict=True):
        pitch = midi_to_pitch(midi)
        if midi == original:
            result.pop(context.event_id, None)
        else:
            result[context.event_id] = pitch
    return result


def _expectation_score(midis: list[int], contexts: list[EventContext], plan: CompositionPlan) -> float:
    events = [
        {
            "type": "note",
            "midi": midi,
            "duration": context.event.get("duration"),
            "offset": float(context.offset),
            "measure": context.measure,
        }
        for midi, context in zip(midis, contexts, strict=True)
    ]
    return float(validate_melody_expectation(events, key=plan.key)["melody_expectation_score"])


def _sign(value: int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _nearest_pitch(reference: int, pitch_class: int, *, low: int, high: int) -> int:
    candidates = [midi for midi in range(low, high + 1) if midi % 12 == pitch_class]
    return min(candidates, key=lambda midi: (abs(midi - reference), midi))


def _pc_distance(left: int, right: int) -> int:
    delta = abs(left - right) % 12
    return min(delta, 12 - delta)


def _melody_pitch_class(
    original: int,
    offset: float,
    index: int,
    measure_index: int,
    chord: tuple[int, int, int],
    scale: tuple[int, ...],
    motif_strategy: str,
    motif_signs: list[int],
    variant: int,
) -> int:
    """Choose a structural chord tone or a motif-directed scale connection."""

    strong_position = int(round(offset * 2)) % 4 == 0
    chord_rotation = (variant + measure_index * (1 + variant % 2)) % len(chord)
    if strong_position:
        return chord[(index // 2 + chord_rotation) % len(chord)]
    nearest_degree = min(range(len(scale)), key=lambda degree: _pc_distance(original % 12, scale[degree]))
    source_direction = motif_signs[(index - 1) % len(motif_signs)] if motif_signs else (1 if index % 2 == 0 else -1)
    if motif_strategy == "inversion_hint":
        source_direction *= -1
    elif motif_strategy == "call_response" and index >= 2:
        source_direction *= -1
    elif motif_strategy == "sequence":
        source_direction = 1 if (measure_index + variant) % 2 == 0 else -1
    if source_direction == 0:
        source_direction = 1 if variant % 2 == 0 else -1
    span = 1 + (variant // 6) % 2
    variation = ((variant // 2) % 3) - 1
    direction = source_direction * span + variation
    if direction == 0:
        direction = source_direction
    return scale[(nearest_degree + direction) % len(scale)]


def _contour_bias(
    variant: int,
    measure_index: int,
    measure_count: int,
    *,
    primary: bool,
    preferred_contours: list[str],
) -> int:
    if not primary:
        return (0, -2, 2)[variant % 3]
    contour = preferred_contours[variant % len(preferred_contours)] if preferred_contours else "arch"
    progress = measure_index / max(1, measure_count - 1)
    arc = {
        "ascending": round(progress * 5),
        "descending": round((1.0 - progress) * 5) - 2,
        "arch": round((1.0 - abs(progress * 2 - 1)) * 7) - 2,
        "valley": 2 - round((1.0 - abs(progress * 2 - 1)) * 5),
        "static": 0,
        "wave": (0, 3, -2, 4, -3)[measure_index % 5],
    }.get(contour, 0)
    register_variant = (0, 2, -2, 5, -5, 7, -7, 12)[(variant // max(1, len(preferred_contours))) % 8]
    return int(arc + register_variant)

"""Proxy musicality checks used to reject empty V0.93 generations."""

from __future__ import annotations

from typing import Any

from evaluation.analysis.music_statistics import parse_pitch_name


RICH_DURATIONS = {"eighth", "sixteenth", "dotted_quarter", "dotted_eighth", "dotted_half"}


def validate_musicality(score_document: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a threshold-oriented musicality proxy report."""

    events = [event for measure in score_document.get("measures", []) for event in measure.get("events", []) if event.get("type") != "rest"]
    note_events = [event for event in events if event.get("type") == "note"]
    total = max(1, len(note_events))
    left_hand = [event for event in note_events if event.get("staff") == "left_hand"]
    durations = [str(event.get("duration", "quarter")) for event in note_events]
    rich = [duration for duration in durations if duration in RICH_DURATIONS]
    quarter_note_dominance = durations.count("quarter") / total
    left_hand_activity = len({measure.get("number") for measure in score_document.get("measures", []) for event in measure.get("events", []) if event.get("staff") == "left_hand" and event.get("type") != "rest"}) / max(1, len(score_document.get("measures", [])))
    rhythmic_variety = len(set(durations)) / max(1, min(5, len(durations)))
    cadence_presence = 1.0 if any(measure.get("cadence") not in {"", "none", None} for measure in score_document.get("measures", [])[-2:]) else 0.0
    motifs = (metadata or {}).get("motifs", {})
    motif_presence = 1.0 if motifs.get("seed_motif") or motifs.get("measures") else 0.0
    warnings: list[str] = []
    errors: list[str] = []
    if left_hand_activity < 0.6:
        warnings.append("left_hand_activity below default intermediate threshold")
    if rhythmic_variety < 0.4:
        warnings.append("rhythmic_variety below default intermediate threshold")
    if cadence_presence < 0.8:
        warnings.append("cadence_presence below threshold")
    if quarter_note_dominance > 0.7:
        warnings.append("quarter_note_dominance above threshold")
    valid = left_hand_activity >= 0.6 and rhythmic_variety >= 0.4 and cadence_presence >= 0.8 and quarter_note_dominance <= 0.7
    return {
        "valid": valid,
        "monophonic_penalty": 0.0 if left_hand else 1.0,
        "quarter_note_dominance": round(quarter_note_dominance, 4),
        "left_hand_activity": round(left_hand_activity, 4),
        "rhythmic_variety": round(max(rhythmic_variety, len(rich) / total), 4),
        "cadence_presence": cadence_presence,
        "motif_presence": motif_presence,
        "warnings": warnings,
        "errors": errors,
    }


def analyze_actual_harmony_style(score_document: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Inspect final ScoreDocument notes to see whether style harmony was realized."""

    metadata = metadata or {}
    profile = dict(metadata.get("generation_profile") or {})
    style = str(profile.get("base_style") if profile.get("style") == "custom" else profile.get("style") or profile.get("base_style") or "classical")
    if style == "cyberpunk":
        style = "electronic"
    harmony_plan = dict(metadata.get("harmony_plan") or {})
    symbols = [str(item) for item in harmony_plan.get("chords", []) or harmony_plan.get("progression", []) or []]
    left_events = [
        event
        for measure in score_document.get("measures", [])
        for event in measure.get("events", [])
        if event.get("staff") == "left_hand" and event.get("type") != "rest"
    ]
    grouped = _left_hand_pitch_groups(score_document)
    group_pcs = [[pitch % 12 for pitch in group] for group in grouped if group]
    contains_sevenths = any(_contains_interval(pcs, {10, 11}) for pcs in group_pcs) or any("7" in symbol for symbol in symbols)
    contains_extensions = any(len(set(pcs)) >= 4 for pcs in group_pcs) or any(any(token in symbol for token in ("9", "13", "alt", "add")) for symbol in symbols)
    left_pcs = _event_pitch_classes(left_events)
    contains_open_fifths = any(_contains_interval(pcs, {7}) and not _contains_interval(pcs, {3, 4}) for pcs in group_pcs) or _contains_interval(left_pcs, {7})
    contains_pedal_point = _pedal_point_score(left_events) >= 0.55 or _measure_pedal_point_score(score_document) >= 0.65
    contains_ostinato = _ostinato_score(left_events) >= 0.55 or _measure_ostinato_score(score_document) >= 0.55
    plain_triad_only = bool(group_pcs) and not contains_sevenths and not contains_extensions and all(_is_plain_triadish(pcs) for pcs in group_pcs)
    progression_text = " ".join(symbols)
    style_score = _style_harmony_score(
        style=style,
        progression_text=progression_text,
        contains_sevenths=contains_sevenths,
        contains_extensions=contains_extensions,
        contains_open_fifths=contains_open_fifths,
        contains_pedal_point=contains_pedal_point,
        contains_ostinato=contains_ostinato,
        plain_triad_only=plain_triad_only,
    )
    warnings: list[str] = []
    if style == "jazz" and plain_triad_only:
        warnings.append("metadata says jazz, but final accompaniment contains plain triads only")
    if style == "jazz" and not (contains_sevenths or contains_extensions):
        warnings.append("jazz accompaniment lacks actual sevenths or extensions")
    if style == "chinese" and not (contains_open_fifths or contains_pedal_point):
        warnings.append("Chinese profile lacks open fifth or pedal realization")
    if style == "electronic" and not (contains_pedal_point or contains_ostinato):
        warnings.append("electronic/cyberpunk profile lacks pedal or ostinato realization")
    return {
        "engine": "actual_harmony_style_validator_v0961",
        "style": style,
        "contains_sevenths": contains_sevenths,
        "contains_extensions": contains_extensions,
        "contains_open_fifths": contains_open_fifths,
        "contains_pedal_point": contains_pedal_point,
        "contains_ostinato": contains_ostinato,
        "plain_triad_only": plain_triad_only,
        "left_hand_event_count": len(left_events),
        "style_harmony_match_score": round(style_score, 4),
        "warnings": warnings,
        "valid": style_score >= 0.65 and not (style == "jazz" and plain_triad_only),
    }


def _left_hand_pitch_groups(score_document: dict[str, Any]) -> list[list[int]]:
    groups: dict[tuple[int, float], list[int]] = {}
    for measure in score_document.get("measures", []):
        number = int(measure.get("number", 0) or 0)
        for event in measure.get("events", []):
            if event.get("staff") != "left_hand" or event.get("type") == "rest":
                continue
            midi = event.get("midi")
            if midi is None:
                midi = parse_pitch_name(str(event.get("pitch", "")))
            if midi is None:
                continue
            groups.setdefault((number, round(float(event.get("offset", 0.0) or 0.0), 3)), []).append(int(midi))
    return [sorted(values) for _, values in sorted(groups.items())]


def _contains_interval(pcs: list[int], targets: set[int]) -> bool:
    unique = sorted(set(pcs))
    for left in unique:
        for right in unique:
            if left == right:
                continue
            if (right - left) % 12 in targets:
                return True
    return False


def _is_plain_triadish(pcs: list[int]) -> bool:
    unique = sorted(set(pcs))
    if len(unique) <= 2:
        return True
    for root in unique:
        intervals = {(pc - root) % 12 for pc in unique}
        if intervals.issubset({0, 3, 4, 7}):
            return True
    return False


def _pedal_point_score(events: list[dict[str, Any]]) -> float:
    pcs = _event_pitch_classes(events)
    if not pcs:
        return 0.0
    most = max(pcs.count(pc) for pc in set(pcs))
    return most / max(1, len(pcs))


def _ostinato_score(events: list[dict[str, Any]]) -> float:
    ordered = []
    for event in events:
        midi = event.get("midi")
        if midi is None:
            midi = parse_pitch_name(str(event.get("pitch", "")))
        if midi is None:
            continue
        ordered.append((int(midi) % 12, str(event.get("duration", ""))))
    if len(ordered) < 4:
        return 0.0
    pairs = list(zip(ordered, ordered[1:], strict=False))
    repeated = sum(1 for left, right in pairs if left == right)
    adjacent_score = repeated / max(1, len(pairs))
    pcs = [item[0] for item in ordered]
    pattern_score = 0.0
    for size in (2, 3, 4):
        if len(pcs) < size * 2:
            continue
        pattern = pcs[:size]
        matches = sum(1 for index, pc in enumerate(pcs) if pc == pattern[index % size])
        pattern_score = max(pattern_score, matches / max(1, len(pcs)))
    return max(adjacent_score, pattern_score)


def _event_pitch_classes(events: list[dict[str, Any]]) -> list[int]:
    pcs = []
    for event in events:
        midi = event.get("midi")
        if midi is None:
            midi = parse_pitch_name(str(event.get("pitch", "")))
        if midi is not None:
            pcs.append(int(midi) % 12)
    return pcs


def _measure_pedal_point_score(score_document: dict[str, Any]) -> float:
    scores = []
    for measure in score_document.get("measures", []):
        events = [event for event in measure.get("events", []) if event.get("staff") == "left_hand" and event.get("type") != "rest"]
        scores.append(_pedal_point_score(events))
    return max(scores or [0.0])


def _measure_ostinato_score(score_document: dict[str, Any]) -> float:
    scores = []
    for measure in score_document.get("measures", []):
        events = [event for event in measure.get("events", []) if event.get("staff") == "left_hand" and event.get("type") != "rest"]
        scores.append(_ostinato_score(events))
    return max(scores or [0.0])


def _style_harmony_score(
    style: str,
    progression_text: str,
    contains_sevenths: bool,
    contains_extensions: bool,
    contains_open_fifths: bool,
    contains_pedal_point: bool,
    contains_ostinato: bool,
    plain_triad_only: bool,
) -> float:
    if style == "jazz":
        score = 0.35
        if any(token in progression_text for token in ("ii7", "V7", "Imaj", "bII", "alt")):
            score += 0.25
        if contains_sevenths:
            score += 0.25
        if contains_extensions:
            score += 0.15
        if plain_triad_only:
            score -= 0.35
        return max(0.0, min(1.0, score))
    if style == "pop":
        return 0.9 if any(cell in progression_text for cell in ("I V vi IV", "vi IV I V", "I vi IV V")) else 0.72
    if style == "classical":
        score = 0.82
        if "V7" in progression_text or "V I" in progression_text:
            score += 0.12
        if contains_extensions:
            score -= 0.18
        return max(0.0, min(1.0, score))
    if style == "chinese":
        return 0.9 if contains_open_fifths or contains_pedal_point else 0.45
    if style == "electronic":
        return 0.9 if contains_pedal_point or contains_ostinato else 0.55
    if style == "romantic":
        score = 0.78
        if any(token in progression_text for token in ("V/V", "V7", "dim")):
            score += 0.15
        if contains_sevenths:
            score += 0.07
        return max(0.0, min(1.0, score))
    return 0.75

"""Expectation-theory-inspired melody validation rules for V0.96."""

from __future__ import annotations

from statistics import mean
from typing import Any

from evaluation.analysis.music_statistics import parse_pitch_name


STABLE_MAJOR = {0, 4, 7}
STABLE_MINOR = {0, 3, 7}
STEP_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def validate_melody_expectation(
    melody_events: list[Any],
    harmony_context: list[Any] | None = None,
    key: str = "C major",
    style_profile: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute practical expectation metrics for a melody event stream."""

    notes = _extract_notes(melody_events)
    if len(notes) < 2:
        return _empty_report(valid=False, reason="not enough melody notes")
    pitches = [note["midi"] for note in notes]
    intervals = [pitches[index + 1] - pitches[index] for index in range(len(pitches) - 1)]
    abs_intervals = [abs(interval) for interval in intervals]
    large_indexes = [index for index, interval in enumerate(abs_intervals) if interval > 5]
    tritone_indexes = [index for index, interval in enumerate(abs_intervals) if interval == 6]

    leap_reversal_rate = _leap_reversal_rate(intervals, large_indexes)
    mean_regression_score = _mean_regression_score(pitches)
    proximity_score = _ratio([interval <= 4 for interval in abs_intervals])
    directional_inertia_score = _directional_inertia_score(intervals)
    registral_return_score = _registral_return_score(pitches)
    gap_fill_score = _gap_fill_score(intervals, large_indexes)
    tonal_anchoring_score = _tonal_anchoring_score(notes, key, harmony_context or [])
    closure_score = _closure_score(notes, key)
    unresolved_tritone_count = _unresolved_tritone_count(intervals, tritone_indexes)
    unresolved_dissonance_count = _unresolved_dissonance_count(notes, key, harmony_context or [])
    large_leap_count = len(large_indexes)
    overall = mean(
        [
            leap_reversal_rate,
            mean_regression_score,
            proximity_score,
            directional_inertia_score,
            registral_return_score,
            gap_fill_score,
            tonal_anchoring_score,
            closure_score,
            max(0.0, 1.0 - unresolved_tritone_count * 0.2),
            max(0.0, 1.0 - unresolved_dissonance_count * 0.1),
        ]
    )
    warnings: list[str] = []
    if large_leap_count:
        warnings.append(f"{large_leap_count} large leaps found")
    if unresolved_tritone_count:
        warnings.append(f"{unresolved_tritone_count} unresolved tritone-like leaps found")
    if closure_score < 0.6:
        warnings.append("weak phrase closure")
    return {
        "engine": "melody_expectation_validator_v096",
        "model_family": "huron_tessitura_expectation_proxy_v1",
        "interpretation": "Auditable structural proxy; not a reproduction of ITPRA and not an aesthetic score.",
        "source_refs": ["Huron 2006 ISBN 9780262083454", "von Hippel and Huron 2000 DOI 10.2307/40285901"],
        "valid": overall >= 0.62 and unresolved_tritone_count == 0,
        "melody_expectation_score": round(float(overall), 4),
        "leap_reversal_rate": round(leap_reversal_rate, 4),
        "mean_regression_score": round(mean_regression_score, 4),
        "proximity_score": round(proximity_score, 4),
        "directional_inertia_score": round(directional_inertia_score, 4),
        "registral_return_score": round(registral_return_score, 4),
        "gap_fill_score": round(gap_fill_score, 4),
        "tonal_anchoring_score": round(tonal_anchoring_score, 4),
        "closure_score": round(closure_score, 4),
        "unresolved_dissonance_count": unresolved_dissonance_count,
        "unresolved_tritone_count": unresolved_tritone_count,
        "large_leap_count": large_leap_count,
        "note_count": len(notes),
        "repairs_applied": list((options or {}).get("repairs_applied", [])),
        "warnings": warnings,
        "style": str((style_profile or {}).get("style") or (style_profile or {}).get("base_style") or ""),
    }


def expectation_score(report: dict[str, Any]) -> float:
    return float(report.get("melody_expectation_score", 0.0) or 0.0)


def _empty_report(valid: bool = True, reason: str = "") -> dict[str, Any]:
    return {
        "engine": "melody_expectation_validator_v096",
        "model_family": "huron_tessitura_expectation_proxy_v1",
        "interpretation": "Auditable structural proxy; not a reproduction of ITPRA and not an aesthetic score.",
        "source_refs": ["Huron 2006 ISBN 9780262083454", "von Hippel and Huron 2000 DOI 10.2307/40285901"],
        "valid": valid,
        "melody_expectation_score": 0.0 if not valid else 1.0,
        "leap_reversal_rate": 1.0,
        "mean_regression_score": 1.0,
        "proximity_score": 1.0,
        "directional_inertia_score": 1.0,
        "registral_return_score": 1.0,
        "gap_fill_score": 1.0,
        "tonal_anchoring_score": 1.0,
        "closure_score": 1.0,
        "unresolved_dissonance_count": 0,
        "unresolved_tritone_count": 0,
        "large_leap_count": 0,
        "note_count": 0,
        "repairs_applied": [],
        "warnings": [reason] if reason else [],
    }


def _extract_notes(events: list[Any]) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if isinstance(event, int):
            notes.append({"midi": event, "duration": 1.0, "offset": float(index), "measure": 1})
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "rest" or event.get("rest"):
            continue
        midi = event.get("midi")
        if midi is None and event.get("pitches"):
            first_pitch = event.get("pitches", [None])[0]
            midi = first_pitch if isinstance(first_pitch, int) else parse_pitch_name(str(first_pitch))
        if midi is None:
            midi = parse_pitch_name(str(event.get("pitch", "")))
        if midi is None:
            continue
        notes.append(
            {
                "midi": int(midi),
                "duration": _duration_quarters(event.get("duration", event.get("duration_quarter", 1.0))),
                "offset": float(event.get("offset", event.get("offset_quarter", event.get("start_quarter", index))) or 0.0),
                "measure": int(event.get("measure", event.get("measure_number", 1)) or 1),
            }
        )
    return sorted(notes, key=lambda item: (item["measure"], item["offset"]))


def _duration_quarters(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return {
        "whole": 4.0,
        "half": 2.0,
        "dotted_half": 3.0,
        "quarter": 1.0,
        "dotted_quarter": 1.5,
        "eighth": 0.5,
        "dotted_eighth": 0.75,
        "sixteenth": 0.25,
    }.get(str(value), 1.0)


def _ratio(items: list[bool]) -> float:
    return sum(1 for item in items if item) / max(1, len(items))


def _sign(value: int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _leap_reversal_rate(intervals: list[int], large_indexes: list[int]) -> float:
    if not large_indexes:
        return 1.0
    checks = []
    for index in large_indexes:
        if index + 1 >= len(intervals):
            checks.append(False)
            continue
        checks.append(_sign(intervals[index]) != _sign(intervals[index + 1]) and abs(intervals[index + 1]) <= 4)
    return _ratio(checks)


def _mean_regression_score(pitches: list[int]) -> float:
    center = mean(pitches)
    checks = []
    for index, pitch in enumerate(pitches[:-1]):
        distance = pitch - center
        if abs(distance) < 5:
            continue
        future = pitches[index + 1 : min(len(pitches), index + 5)]
        if not future:
            checks.append(False)
        else:
            checks.append(abs(future[-1] - center) < abs(distance))
    return _ratio(checks) if checks else 1.0


def _directional_inertia_score(intervals: list[int]) -> float:
    run = 0
    previous = 0
    excessive = 0
    for interval in intervals:
        current = _sign(interval)
        if current == 0:
            run = 0
            previous = 0
            continue
        run = run + 1 if current == previous else 1
        previous = current
        if run > 5:
            excessive += 1
    return max(0.0, 1.0 - excessive / max(1, len(intervals)))


def _registral_return_score(pitches: list[int]) -> float:
    checks = []
    for index in range(1, len(pitches) - 1):
        previous_pitch, pitch, next_pitch = pitches[index - 1], pitches[index], pitches[index + 1]
        if pitch > previous_pitch and pitch > next_pitch:
            future = pitches[index + 1 : min(len(pitches), index + 4)]
            checks.append(any(item < pitch for item in future))
        if pitch < previous_pitch and pitch < next_pitch:
            future = pitches[index + 1 : min(len(pitches), index + 4)]
            checks.append(any(item > pitch for item in future))
    return _ratio(checks) if checks else 1.0


def _gap_fill_score(intervals: list[int], large_indexes: list[int]) -> float:
    if not large_indexes:
        return 1.0
    checks = []
    for index in large_indexes:
        if index + 1 >= len(intervals):
            checks.append(False)
        else:
            checks.append(_sign(intervals[index]) != _sign(intervals[index + 1]) and abs(intervals[index + 1]) <= max(4, abs(intervals[index]) - 3))
    return _ratio(checks)


def _tonal_anchoring_score(notes: list[dict[str, Any]], key: str, harmony_context: list[Any]) -> float:
    stable = _stable_pcs_for_key(key)
    checks = []
    last_by_measure: dict[int, dict[str, Any]] = {}
    for note in notes:
        last_by_measure[note["measure"]] = note
        if abs(note["offset"] - round(note["offset"])) < 0.01:
            checks.append(note["midi"] % 12 in stable)
    for note in last_by_measure.values():
        checks.append(note["midi"] % 12 in stable)
    return _ratio(checks) if checks else 1.0


def _closure_score(notes: list[dict[str, Any]], key: str) -> float:
    if not notes:
        return 0.0
    stable = _stable_pcs_for_key(key)
    last = notes[-1]
    previous_durations = [note["duration"] for note in notes[:-1]] or [last["duration"]]
    stable_pitch = 1.0 if last["midi"] % 12 in stable else 0.35
    rhythmic_settle = 1.0 if last["duration"] >= mean(previous_durations) else 0.55
    direction_settle = 1.0
    if len(notes) >= 2:
        direction_settle = 1.0 if abs(last["midi"] - notes[-2]["midi"]) <= 7 else 0.45
    return mean([stable_pitch, rhythmic_settle, direction_settle])


def _unresolved_tritone_count(intervals: list[int], tritone_indexes: list[int]) -> int:
    count = 0
    for index in tritone_indexes:
        if index + 1 >= len(intervals):
            count += 1
        elif _sign(intervals[index]) == _sign(intervals[index + 1]) or abs(intervals[index + 1]) > 4:
            count += 1
    return count


def _unresolved_dissonance_count(notes: list[dict[str, Any]], key: str, harmony_context: list[Any]) -> int:
    stable = _stable_pcs_for_key(key)
    count = 0
    for index, note in enumerate(notes[:-1]):
        strong = abs(note["offset"] - round(note["offset"])) < 0.01 or note["duration"] >= 1.0
        if not strong or note["midi"] % 12 in stable:
            continue
        next_note = notes[index + 1]
        if next_note["midi"] % 12 not in stable or abs(next_note["midi"] - note["midi"]) > 2:
            count += 1
    return count


def _stable_pcs_for_key(key: str) -> set[int]:
    tonic = str(key or "C major").split()[0].replace("-flat", "b")
    root = STEP_TO_PC.get(tonic[0].upper(), 0)
    if len(tonic) > 1:
        root += 1 if tonic[1] == "#" else -1 if tonic[1].lower() == "b" else 0
    base = STABLE_MINOR if "minor" in str(key).lower() else STABLE_MAJOR
    return {(root + pc) % 12 for pc in base}

"""Melodic interval validation and lightweight repair for generated lines."""

from __future__ import annotations

from statistics import mean
from typing import Any

from backend.generation.musicality.melodic_style_engine import DEGREE_TO_OFFSET


STEP_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def analyze_melody_intervals(notes: list[int]) -> dict[str, Any]:
    intervals = [int(b) - int(a) for a, b in zip(notes, notes[1:], strict=False)]
    abs_intervals = [abs(value) for value in intervals]
    return {
        "intervals": intervals,
        "tritone_count": sum(1 for value in abs_intervals if value == 6),
        "large_leap_count": sum(1 for value in abs_intervals if value > 7),
        "same_direction_step_run_max": _same_direction_step_run(intervals),
        "range_semitones": max(notes) - min(notes) if notes else 0,
        "average_interval": round(mean(abs_intervals), 4) if abs_intervals else 0.0,
    }


def validate_melodic_line(
    notes: list[int],
    key: str,
    mode: str,
    style_profile: dict[str, Any],
    difficulty: str,
) -> dict[str, Any]:
    analysis = analyze_melody_intervals(notes)
    intervals = list(analysis["intervals"])
    total = max(1, len(intervals))
    unresolved = _unresolved_leap_count(intervals)
    tritones = int(analysis["tritone_count"])
    run_max = int(analysis["same_direction_step_run_max"])
    warnings: list[str] = []
    if tritones:
        warnings.append("unresolved tritone-like melodic leap detected")
    if unresolved:
        warnings.append("large leap without contrary stepwise recovery detected")
    if run_max > 5:
        warnings.append("same-direction stepwise run is too long")
    if difficulty == "beginner" and int(analysis["large_leap_count"]) > 1:
        warnings.append("beginner melody contains too many large leaps")
    valid = not warnings
    return {
        "valid": valid,
        "tritone_violation_rate": round(tritones / total, 4),
        "unresolved_leap_rate": round(unresolved / total, 4),
        "large_leap_count": int(analysis["large_leap_count"]),
        "stepwise_recovery_rate": round(1.0 - min(1.0, unresolved / total), 4),
        "near_duplicate_melody_score": 0.0,
        "same_direction_step_run_max": run_max,
        "singability_score": _singability_score(analysis, difficulty),
        "warnings": warnings,
        "errors": [] if valid else warnings,
        "key": key,
        "mode": mode,
        "pitch_vocabulary": style_profile.get("pitch_vocabulary", "diatonic"),
    }


def repair_melodic_line(
    notes: list[int],
    key: str,
    mode: str,
    style_profile: dict[str, Any],
    difficulty: str,
) -> list[int]:
    repaired = [int(note) for note in notes]
    if not repaired:
        return repaired
    if style_profile.get("pitch_vocabulary") == "pentatonic":
        repaired = [_snap_to_vocabulary(note, key, ["1", "2", "3", "5", "6"]) for note in repaired]
    for index in range(1, len(repaired)):
        interval = repaired[index] - repaired[index - 1]
        if abs(interval) == 6:
            repaired[index] += -1 if interval > 0 else 1
        if difficulty == "beginner" and abs(repaired[index] - repaired[index - 1]) > 7:
            repaired[index] = repaired[index - 1] + (5 if repaired[index] > repaired[index - 1] else -5)
    for index in range(1, len(repaired) - 1):
        interval = repaired[index] - repaired[index - 1]
        next_interval = repaired[index + 1] - repaired[index]
        if abs(interval) > 7 and (interval * next_interval >= 0 or abs(next_interval) > 2):
            repaired[index + 1] = repaired[index] + (-2 if interval > 0 else 2)
    repaired = _break_long_step_runs(repaired)
    if style_profile.get("pitch_vocabulary") == "pentatonic":
        repaired = [_snap_to_vocabulary(note, key, ["1", "2", "3", "5", "6"]) for note in repaired]
    return repaired


def validate_cross_measure_melody_events(
    melody_events: list[dict[str, Any]],
    key: str,
    mode: str,
    style_profile: dict[str, Any],
    difficulty: str,
) -> dict[str, Any]:
    """Validate melody continuity between the end of one measure and the next."""

    ordered = sorted(
        [event for event in melody_events if event.get("midi") is not None],
        key=lambda event: (int(event.get("measure_number", 1) or 1), float(event.get("offset", 0.0) or 0.0)),
    )
    by_measure: dict[int, list[dict[str, Any]]] = {}
    for event in ordered:
        by_measure.setdefault(int(event.get("measure_number", 1) or 1), []).append(event)
    transitions: list[dict[str, Any]] = []
    tritone_count = 0
    large_leap_count = 0
    unresolved_count = 0
    max_interval = 0
    phrase_boundary_exceptions: list[dict[str, Any]] = []
    measure_numbers = sorted(by_measure)
    for left_measure, right_measure in zip(measure_numbers, measure_numbers[1:], strict=False):
        if right_measure != left_measure + 1:
            continue
        left_event = by_measure[left_measure][-1]
        right_event = by_measure[right_measure][0]
        interval = int(right_event["midi"]) - int(left_event["midi"])
        abs_interval = abs(interval)
        max_interval = max(max_interval, abs_interval)
        recovery = _next_interval_in_measure(by_measure[right_measure])
        unresolved = _is_unresolved_cross_measure_leap(interval, recovery)
        is_tritone = abs_interval == 6
        is_large = abs_interval > 12 or (difficulty in {"beginner", "intermediate"} and abs_interval > 7)
        is_phrase_boundary = left_measure % 4 == 0
        if is_tritone:
            tritone_count += 1
        if is_large:
            large_leap_count += 1
        if (is_tritone or is_large or abs_interval > 7) and unresolved:
            unresolved_count += 1
        transition = {
            "from_measure": left_measure,
            "to_measure": right_measure,
            "from_event_id": left_event.get("event_id", ""),
            "to_event_id": right_event.get("event_id", ""),
            "interval": interval,
            "abs_interval": abs_interval,
            "recovery_interval": recovery,
            "tritone": is_tritone,
            "large_leap": is_large,
            "unresolved": unresolved,
            "phrase_boundary": is_phrase_boundary,
        }
        transitions.append(transition)
        if is_phrase_boundary and (is_tritone or is_large):
            phrase_boundary_exceptions.append(transition)

    total = max(1, len(transitions))
    warnings: list[str] = []
    if tritone_count:
        warnings.append("cross-measure tritone-like leap detected")
    if large_leap_count:
        warnings.append("cross-measure large leap detected")
    if unresolved_count:
        warnings.append("unresolved cross-measure leap detected")
    step_run = _same_direction_step_run([int(b["midi"]) - int(a["midi"]) for a, b in zip(ordered, ordered[1:], strict=False)])
    if step_run > 5:
        warnings.append("excessive same-direction stepwise run crosses measure boundaries")
    valid = not warnings
    return {
        "valid": valid,
        "source": "primary_melody_line",
        "key": key,
        "mode": mode,
        "difficulty": difficulty,
        "cross_measure_tritone_rate": round(tritone_count / total, 4),
        "cross_measure_large_leap_count": large_leap_count,
        "unresolved_cross_measure_leap_count": unresolved_count,
        "max_cross_measure_interval": max_interval,
        "same_direction_step_run_max": step_run,
        "phrase_boundary_exceptions": phrase_boundary_exceptions,
        "transitions": transitions,
        "repairs_applied": [],
        "warnings": warnings,
        "errors": [] if valid else warnings,
        "pitch_vocabulary": style_profile.get("pitch_vocabulary", "diatonic"),
    }


def repair_cross_measure_melody(
    score_document: dict[str, Any],
    melody_events: list[dict[str, Any]],
    key: str,
    mode: str,
    style_profile: dict[str, Any],
    difficulty: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Repair invalid cross-measure openings while preserving rhythm and left hand."""

    import copy

    repaired_score = copy.deepcopy(score_document or {})
    report = validate_cross_measure_melody_events(melody_events, key, mode, style_profile, difficulty)
    repairs: list[dict[str, Any]] = []
    if report.get("valid"):
        report["repairs_applied"] = repairs
        return repaired_score, report
    event_index = {
        str(event.get("event_id")): event
        for measure in repaired_score.get("measures", [])
        for event in measure.get("events", [])
    }
    by_id = {str(event.get("event_id")): event for event in melody_events}
    for transition in report.get("transitions", []):
        if not (transition.get("tritone") or transition.get("large_leap") or transition.get("unresolved")):
            continue
        target_id = str(transition.get("to_event_id") or "")
        source_id = str(transition.get("from_event_id") or "")
        target_event = event_index.get(target_id)
        source_event = by_id.get(source_id)
        if not target_event or not source_event:
            continue
        source_midi = int(source_event.get("midi", 60))
        interval = int(transition.get("interval", 0) or 0)
        direction = 1 if interval >= 0 else -1
        if abs(interval) == 6:
            target_midi = source_midi + (5 * direction)
        elif abs(interval) > 12:
            target_midi = source_midi + (7 * direction)
        elif abs(interval) > 7:
            target_midi = source_midi + (5 * direction)
        else:
            continue
        old_pitch = str(target_event.get("pitch", ""))
        if style_profile.get("pitch_vocabulary") == "pentatonic":
            target_midi = _snap_to_vocabulary(target_midi, key, ["1", "2", "3", "5", "6"])
        target_event["pitch"] = _midi_to_pitch(max(48, min(84, target_midi)))
        repairs.append(
            {
                "event_id": target_id,
                "from_measure": transition.get("from_measure"),
                "to_measure": transition.get("to_measure"),
                "old_pitch": old_pitch,
                "new_pitch": target_event["pitch"],
                "reason": "cross_measure_tritone" if abs(interval) == 6 else "cross_measure_large_leap",
            }
        )
    report["repairs_applied"] = repairs
    return repaired_score, report


def _unresolved_leap_count(intervals: list[int]) -> int:
    count = 0
    for index, interval in enumerate(intervals[:-1]):
        if abs(interval) <= 7:
            continue
        recovery = intervals[index + 1]
        if interval * recovery >= 0 or abs(recovery) > 2:
            count += 1
    return count


def _next_interval_in_measure(events: list[dict[str, Any]]) -> int | None:
    if len(events) < 2:
        return None
    return int(events[1]["midi"]) - int(events[0]["midi"])


def _is_unresolved_cross_measure_leap(interval: int, recovery: int | None) -> bool:
    if abs(interval) <= 7 and abs(interval) != 6:
        return False
    if recovery is None:
        return True
    return interval * recovery >= 0 or abs(recovery) > 2


def _same_direction_step_run(intervals: list[int]) -> int:
    longest = 0
    current = 0
    direction = 0
    for interval in intervals:
        sign = 1 if interval > 0 else -1 if interval < 0 else 0
        if abs(interval) in {1, 2} and sign:
            current = current + 1 if sign == direction else 1
            direction = sign
        else:
            current = 0
            direction = 0
        longest = max(longest, current)
    return longest


def _break_long_step_runs(notes: list[int]) -> list[int]:
    out = list(notes)
    intervals = [b - a for a, b in zip(out, out[1:], strict=False)]
    run = 0
    direction = 0
    for index, interval in enumerate(intervals, start=1):
        sign = 1 if interval > 0 else -1 if interval < 0 else 0
        if abs(interval) in {1, 2} and sign:
            run = run + 1 if sign == direction else 1
            direction = sign
        else:
            run = 0
            direction = 0
        if run > 5:
            out[index] = out[index - 1] - (2 * direction)
            run = 0
            direction = -direction
    return out


def _singability_score(analysis: dict[str, Any], difficulty: str) -> float:
    score = 1.0
    score -= min(0.35, int(analysis["tritone_count"]) * 0.12)
    score -= min(0.25, int(analysis["large_leap_count"]) * (0.08 if difficulty != "beginner" else 0.16))
    score -= min(0.2, max(0, int(analysis["same_direction_step_run_max"]) - 5) * 0.04)
    return round(max(0.0, min(1.0, score)), 4)


def _snap_to_vocabulary(note: int, key: str, degrees: list[str]) -> int:
    tonic = _tonic_pc(key)
    pcs = [((tonic + DEGREE_TO_OFFSET[degree]) % 12) for degree in degrees]
    candidates = []
    for octave_shift in range(-2, 3):
        base_octave = (note // 12 + octave_shift) * 12
        candidates.extend(base_octave + pc for pc in pcs)
    return min(candidates, key=lambda candidate: abs(candidate - note))


def _tonic_pc(key: str) -> int:
    token = str(key or "C").split()[0].replace("-flat", "b")
    pc = STEP_TO_PC.get(token[:1].upper(), 0)
    if len(token) > 1:
        pc += 1 if token[1] == "#" else -1 if token[1].lower() == "b" else 0
    return pc % 12


def _midi_to_pitch(midi: int) -> str:
    names = {
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
    step, alter = names[int(midi) % 12]
    accidental = "#" if alter > 0 else "b" if alter < 0 else ""
    return f"{step}{accidental}{int(midi) // 12 - 1}"

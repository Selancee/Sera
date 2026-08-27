"""Validate normalized ScoreDocument notation grammar."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from backend.notation.beat_grouping import beat_grouping_warnings
from backend.notation.duration_math import DURATION_TO_FRACTION, duration_to_fraction
from backend.notation.meter_rules import get_meter_rule, measure_capacity_beats


def validate_score_document_notation(score_document: dict[str, Any]) -> dict[str, Any]:
    """Return notation grammar validity for a ScoreDocument."""

    meter = str(score_document.get("global", {}).get("meter", "4/4"))
    rule = get_meter_rule(meter)
    capacity = measure_capacity_beats(meter)
    warnings: list[str] = []
    errors: list[str] = []
    measure_duration_valid = True
    dotted_duration_valid = True
    voice_consistency_valid = True
    staff_consistency_valid = True
    rest_grouping_valid = True
    beat_grouping_valid = True
    tie_valid = True

    for measure in score_document.get("measures", []):
        number = int(measure.get("number", 0) or 0)
        events = list(measure.get("events") or [])
        if not events:
            errors.append(f"Measure {number} is empty.")
            measure_duration_valid = False
            continue
        grouping_warnings = beat_grouping_warnings(events, meter)
        warnings.extend(f"Measure {number}: {warning}" for warning in grouping_warnings)
        rest_grouping_valid = rest_grouping_valid and not grouping_warnings
        by_group: dict[tuple[str, int], Fraction] = {}
        for event in events:
            staff = str(event.get("staff", "right_hand"))
            voice = int(event.get("voice", 1) or 1)
            if staff not in {"right_hand", "left_hand"}:
                staff_consistency_valid = False
                errors.append(f"Measure {number} event {event.get('event_id')} has invalid staff {staff}.")
            if voice < 1:
                voice_consistency_valid = False
                errors.append(f"Measure {number} event {event.get('event_id')} has invalid voice {voice}.")
            duration_label = str(event.get("duration", "quarter"))
            if duration_label.replace("-", "_") not in DURATION_TO_FRACTION:
                dotted_duration_valid = False
                errors.append(f"Measure {number} event {event.get('event_id')} has unknown duration {duration_label}.")
            start = Fraction(str(event.get("offset", 0)))
            duration = duration_to_fraction(duration_label)
            if start < 0:
                measure_duration_valid = False
                errors.append(f"Measure {number} event {event.get('event_id')} has negative offset.")
            if start + duration > capacity:
                measure_duration_valid = False
                errors.append(f"Measure {number} event {event.get('event_id')} exceeds {meter}.")
            by_group[(staff, voice)] = max(by_group.get((staff, voice), Fraction(0, 1)), start + duration)
            tie = event.get("tie")
            if tie not in {None, "", "start", "stop", "continue"}:
                tie_valid = False
                errors.append(f"Measure {number} event {event.get('event_id')} has invalid tie value {tie}.")
        for (staff, voice), end in by_group.items():
            if end != capacity:
                measure_duration_valid = False
                errors.append(f"Measure {number} {staff} voice {voice} ends at {float(end)} instead of {float(capacity)}.")
    return {
        "valid": not errors,
        "meter_valid": rule.meter == meter or meter not in {"4/4", "3/4", "6/8"},
        "measure_duration_valid": measure_duration_valid,
        "beat_grouping_valid": beat_grouping_valid,
        "rest_grouping_valid": rest_grouping_valid,
        "dotted_duration_valid": dotted_duration_valid,
        "tie_valid": tie_valid,
        "voice_consistency_valid": voice_consistency_valid,
        "staff_consistency_valid": staff_consistency_valid,
        "warnings": warnings,
        "errors": errors,
    }

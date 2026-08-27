"""Rest grouping helpers."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from backend.notation.duration_math import fraction_to_duration_options, fraction_to_float
from backend.notation.meter_rules import beat_groups


def grouped_rests_for_gap(measure_id: str, staff: str, voice: int, start: Fraction, end: Fraction, meter: str) -> list[dict[str, Any]]:
    """Create rests for a gap, respecting meter group boundaries where possible."""

    rests: list[dict[str, Any]] = []
    cursor = start
    serial = 1
    boundaries = [group_end for _, group_end in beat_groups(meter) if start < group_end < end] + [end]
    for boundary in boundaries:
        duration = boundary - cursor
        if duration <= 0:
            continue
        for label in fraction_to_duration_options(duration):
            label_duration = _duration_fraction(label)
            rests.append(
                {
                    "event_id": f"{measure_id}_rest_{staff}_{voice}_{serial}",
                    "type": "rest",
                    "pitch": "",
                    "duration": label,
                    "offset": fraction_to_float(cursor),
                    "voice": voice,
                    "staff": staff,
                    "tie": None,
                    "dynamic": "mf",
                    "articulations": [],
                    "selected": False,
                }
            )
            cursor += label_duration
            serial += 1
    return rests


def _duration_fraction(label: str) -> Fraction:
    from backend.notation.duration_math import duration_to_fraction

    return duration_to_fraction(label)

"""Split overlong events and mark simple ties."""

from __future__ import annotations

import copy
from fractions import Fraction
from typing import Any

from backend.notation.duration_math import fraction_to_duration_options, fraction_to_float
from backend.notation.meter_rules import measure_capacity_beats


def split_event_at_barline(event: dict[str, Any], offset: Fraction, duration: Fraction, meter: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return the in-measure event plus overflow events starting at the next bar."""

    capacity = measure_capacity_beats(meter)
    room = max(Fraction(0, 1), capacity - offset)
    if duration <= room:
        kept = copy.deepcopy(event)
        kept["offset"] = fraction_to_float(offset)
        kept["duration"] = fraction_to_duration_options(duration)[0]
        return kept, []

    kept = copy.deepcopy(event)
    kept["offset"] = fraction_to_float(offset)
    kept["duration"] = fraction_to_duration_options(room)[0]
    if kept.get("type") != "rest":
        kept["tie"] = "start"

    overflow: list[dict[str, Any]] = []
    remaining = duration - room
    source_event_id = str(event.get("event_id", "event"))
    continuation_index = 0
    while remaining > 0:
        continuation_index += 1
        chunk = min(remaining, capacity)
        extra = copy.deepcopy(event)
        extra["event_id"] = f"{source_event_id}~tie{continuation_index}"
        extra["tie_origin_event_id"] = source_event_id
        extra["offset"] = 0.0
        extra["duration"] = fraction_to_duration_options(chunk)[0]
        if extra.get("type") != "rest":
            extra["tie"] = "stop" if remaining == chunk else "continue"
        overflow.append(extra)
        remaining -= chunk
    return kept, overflow

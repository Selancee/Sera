"""Beat grouping checks for generated notation."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from backend.notation.duration_math import duration_to_fraction
from backend.notation.meter_rules import beat_groups


def event_crosses_important_boundary(event: dict[str, Any], meter: str) -> bool:
    """Return whether an event crosses a meter group boundary."""

    start = Fraction(str(event.get("offset", 0)))
    end = start + duration_to_fraction(str(event.get("duration", "quarter")))
    return any(start < boundary < end for _, boundary in beat_groups(meter))


def beat_grouping_warnings(events: list[dict[str, Any]], meter: str) -> list[str]:
    """Return lightweight warnings for events that obscure beat groups."""

    warnings: list[str] = []
    for event in events:
        if event.get("type") == "rest" and event_crosses_important_boundary(event, meter):
            warnings.append(f"Rest {event.get('event_id', '')} crosses a beat group boundary.")
    return warnings

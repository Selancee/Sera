"""Rational duration math for ScoreDocument notation grammar."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Iterable


DURATION_TO_FRACTION: dict[str, Fraction] = {
    "whole": Fraction(4, 1),
    "half": Fraction(2, 1),
    "quarter": Fraction(1, 1),
    "eighth": Fraction(1, 2),
    "sixteenth": Fraction(1, 4),
    "dotted_half": Fraction(3, 1),
    "dotted-quarter": Fraction(3, 2),
    "dotted_quarter": Fraction(3, 2),
    "dotted eighth": Fraction(3, 4),
    "dotted-eighth": Fraction(3, 4),
    "dotted_eighth": Fraction(3, 4),
    "triplet_eighth": Fraction(1, 3),
    "triplet_eighth_basic": Fraction(1, 3),
}

FRACTION_TO_DURATION: dict[Fraction, str] = {
    Fraction(4, 1): "whole",
    Fraction(3, 1): "dotted_half",
    Fraction(2, 1): "half",
    Fraction(3, 2): "dotted_quarter",
    Fraction(1, 1): "quarter",
    Fraction(3, 4): "dotted_eighth",
    Fraction(1, 2): "eighth",
    Fraction(1, 4): "sixteenth",
    Fraction(1, 3): "triplet_eighth",
}


def duration_to_fraction(duration: str) -> Fraction:
    """Return quarter-note units for a duration label."""

    clean = str(duration or "quarter").strip().replace("-", "_")
    return DURATION_TO_FRACTION.get(clean, Fraction(1, 1))


def fraction_to_duration_options(value: Fraction) -> list[str]:
    """Return one or more duration labels that exactly add to ``value``."""

    value = Fraction(value)
    if value in FRACTION_TO_DURATION:
        return [FRACTION_TO_DURATION[value]]
    remaining = value
    result: list[str] = []
    for fraction, label in sorted(FRACTION_TO_DURATION.items(), reverse=True):
        if fraction == Fraction(1, 3):
            continue
        while remaining >= fraction:
            result.append(label)
            remaining -= fraction
    if remaining:
        result.extend(["sixteenth"] * max(1, int(round(float(remaining / Fraction(1, 4))))))
    return result or ["quarter"]


def sum_durations(events: Iterable[dict[str, Any]]) -> Fraction:
    """Return the additive duration of an event sequence."""

    total = Fraction(0, 1)
    for event in events:
        total += duration_to_fraction(str(event.get("duration", "quarter")))
    return total


def fits_in_measure(events: Iterable[dict[str, Any]], meter: str) -> bool:
    """Return whether events fit the meter capacity additively."""

    from backend.notation.meter_rules import measure_capacity_beats

    return sum_durations(events) <= measure_capacity_beats(meter)


def fraction_to_float(value: Fraction) -> float:
    """Store a rational value in the existing ScoreDocument float offset field."""

    return round(float(value), 6)

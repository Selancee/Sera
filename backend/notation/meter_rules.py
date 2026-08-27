"""Meter-specific notation rules for V0.93 normalization."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class MeterRule:
    meter: str
    capacity_quarters: Fraction
    strong_beats: tuple[Fraction, ...]
    groups: tuple[tuple[Fraction, Fraction], ...]
    compound: bool = False


RULES: dict[str, MeterRule] = {
    "4/4": MeterRule(
        meter="4/4",
        capacity_quarters=Fraction(4, 1),
        strong_beats=(Fraction(0, 1), Fraction(2, 1)),
        groups=((Fraction(0, 1), Fraction(1, 1)), (Fraction(1, 1), Fraction(2, 1)), (Fraction(2, 1), Fraction(3, 1)), (Fraction(3, 1), Fraction(4, 1))),
    ),
    "3/4": MeterRule(
        meter="3/4",
        capacity_quarters=Fraction(3, 1),
        strong_beats=(Fraction(0, 1),),
        groups=((Fraction(0, 1), Fraction(1, 1)), (Fraction(1, 1), Fraction(2, 1)), (Fraction(2, 1), Fraction(3, 1))),
    ),
    "6/8": MeterRule(
        meter="6/8",
        capacity_quarters=Fraction(3, 1),
        strong_beats=(Fraction(0, 1), Fraction(3, 2)),
        groups=((Fraction(0, 1), Fraction(3, 2)), (Fraction(3, 2), Fraction(3, 1))),
        compound=True,
    ),
}


def get_meter_rule(meter: str) -> MeterRule:
    """Return a known meter rule, defaulting to 4/4."""

    return RULES.get(str(meter or "4/4"), RULES["4/4"])


def measure_capacity_beats(meter: str) -> Fraction:
    """Return measure capacity in quarter-note units."""

    return get_meter_rule(meter).capacity_quarters


def beat_groups(meter: str) -> list[tuple[Fraction, Fraction]]:
    """Return beat-group boundaries in quarter-note units."""

    return list(get_meter_rule(meter).groups)


def next_group_boundary(offset: Fraction, meter: str) -> Fraction:
    """Return the next readable beat-group boundary after ``offset``."""

    rule = get_meter_rule(meter)
    for _, end in rule.groups:
        if offset < end:
            return end
    return rule.capacity_quarters

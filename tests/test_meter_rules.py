from fractions import Fraction

from backend.notation.meter_rules import beat_groups, measure_capacity_beats


def test_meter_capacities_and_groups() -> None:
    assert measure_capacity_beats("4/4") == Fraction(4, 1)
    assert measure_capacity_beats("3/4") == Fraction(3, 1)
    assert measure_capacity_beats("6/8") == Fraction(3, 1)
    assert beat_groups("6/8") == [(Fraction(0, 1), Fraction(3, 2)), (Fraction(3, 2), Fraction(3, 1))]

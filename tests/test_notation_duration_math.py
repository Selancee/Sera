from fractions import Fraction

from backend.notation.duration_math import duration_to_fraction, fits_in_measure, fraction_to_duration_options


def test_dotted_duration_uses_rational_math() -> None:
    assert duration_to_fraction("dotted_quarter") == Fraction(3, 2)
    assert duration_to_fraction("dotted_eighth") == Fraction(3, 4)
    assert "dotted_quarter" in fraction_to_duration_options(Fraction(3, 2))


def test_duration_fit_avoids_float_equality() -> None:
    events = [{"duration": "dotted_quarter"}, {"duration": "eighth"}, {"duration": "half"}]
    assert fits_in_measure(events, "4/4") is True

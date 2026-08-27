from fractions import Fraction

from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.rhythm_engine import RhythmEngine
from backend.notation.meter_rules import measure_capacity_beats


def test_rhythm_engine_patterns_fit_supported_meters() -> None:
    for meter in ["4/4", "3/4", "6/8"]:
        plan = RhythmEngine().generate(GenerationProfile(meter=meter), 8)
        capacity = measure_capacity_beats(meter)
        for measure in plan["measures"]:
            total = sum(Fraction(str(event["duration_quarters"])) for event in measure["events"])
            assert total == capacity

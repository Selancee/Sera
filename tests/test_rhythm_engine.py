from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.rhythm_engine import RhythmEngine


def test_rhythm_engine_uses_varied_dotted_and_eighth_patterns() -> None:
    profile = GenerationProfile(meter="4/4", difficulty="intermediate", rhythmic_density="high", requires_dotted_rhythm=True)
    plan = RhythmEngine().generate(profile, 8)

    pattern_ids = [measure["pattern_id"] for measure in plan["measures"]]
    assert plan["unique_pattern_count"] >= 3
    assert any("dotted" in pattern for pattern in pattern_ids)
    assert any("eighth" in pattern for pattern in pattern_ids)
    assert all(pattern_ids[index : index + 3] != [pattern_ids[index]] * 3 for index in range(len(pattern_ids) - 2))


def test_beginner_rhythm_avoids_sixteenth_patterns() -> None:
    profile = GenerationProfile(meter="4/4", difficulty="beginner", rhythmic_density="high")
    plan = RhythmEngine().generate(profile, 4)
    assert all("sixteenth" not in measure["pattern_id"] for measure in plan["measures"])

import random

from backend.generation.musicality.harmony_profile import build_harmony_profile, select_progression_from_profile


def test_harmony_profiles_differ_by_style() -> None:
    jazz = build_harmony_profile({"style": "jazz"}, "F major", "major", "advanced")
    chinese = build_harmony_profile({"style": "chinese"}, "C major", "major", "intermediate")
    pop = build_harmony_profile({"style": "pop"}, "C major", "major", "intermediate")

    assert "13th" in jazz["vocabulary"]
    assert "open_fifth" in chinese["vocabulary"]
    assert "add9" in pop["vocabulary"]
    assert jazz["progressions"] != pop["progressions"]


def test_select_progression_from_profile_adds_final_cadence() -> None:
    profile = build_harmony_profile({"style": "classical"}, "C major", "major", "intermediate")
    selected = select_progression_from_profile(profile, 8, random.Random(1))

    assert selected["chords"][-2:] == ["V7", "I"]
    assert selected["progression_source"] == "classical_harmony_profile"

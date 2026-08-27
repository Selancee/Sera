from backend.generation.musicality.harmony_profile import build_harmony_profile


def test_pop_harmony_profile_matches_pop_vocabulary() -> None:
    profile = build_harmony_profile({"style": "pop"}, "C major", "major", "intermediate")

    assert ["I", "V", "vi", "IV"] in profile["progressions"]
    assert "slash_chord" in profile["vocabulary"]

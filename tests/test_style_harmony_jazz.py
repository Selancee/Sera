from backend.generation.musicality.harmony_profile import build_harmony_profile


def test_jazz_harmony_profile_contains_extensions_and_substitution() -> None:
    profile = build_harmony_profile({"style": "jazz"}, "F major", "major", "advanced")

    assert profile["allows_extensions"] is True
    assert "tritone_sub" in profile["vocabulary"]
    assert any("ii7" in progression for progression in profile["progressions"])

from backend.generation.musicality.harmony_profile import build_harmony_profile


def test_chinese_harmony_profile_uses_pentatonic_open_logic() -> None:
    profile = build_harmony_profile({"style": "chinese"}, "D major", "major", "intermediate")

    assert "pentatonic_verticalization" in profile["vocabulary"]
    assert "quartal" in profile["vocabulary"]
    assert profile["allows_parallel_fifths"] is True

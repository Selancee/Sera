from backend.generation.musicality.harmony_profile import build_harmony_profile


def test_classical_harmony_profile_sets_voice_leading_constraints() -> None:
    profile = build_harmony_profile({"style": "classical"}, "C major", "major", "intermediate")

    assert "leading_tone_resolution" in profile["vocabulary"]
    assert profile["allows_parallel_fifths"] is False

from backend.generation.musicality.harmony_profile import build_harmony_profile
from backend.generation.musicality.voice_leading_validator import validate_voice_leading


def test_classical_voice_leading_penalizes_parallel_fifths() -> None:
    profile = build_harmony_profile({"style": "classical"}, "C major", "major", "intermediate")
    report = validate_voice_leading([[60, 67], [62, 69]], profile)

    assert report["parallel_fifths_count"] >= 1
    assert report["style_harmony_match_score"] < 1.0


def test_chinese_profile_allows_open_fifth_motion() -> None:
    profile = build_harmony_profile({"style": "chinese"}, "C major", "major", "intermediate")
    report = validate_voice_leading([[48, 55], [50, 57]], profile)

    assert report["parallel_fifths_count"] >= 1
    assert report["style_harmony_match_score"] == 1.0

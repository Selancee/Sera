from backend.generation.musicality.harmony_profile import build_harmony_profile
from backend.generation.musicality.voicing_engine import voice_chord


def test_jazz_voicing_can_be_rootless_extended() -> None:
    profile = build_harmony_profile({"style": "jazz"}, "F major", "major", "advanced")
    voicing = voice_chord("V7", profile, register="left_hand", role="accompaniment")

    assert voicing["rootless"] is True
    assert len(voicing["voicing"]) >= 4
    assert voicing["playability_score"] > 0.5


def test_chinese_voicing_uses_open_fifth_or_quartal_shape() -> None:
    profile = build_harmony_profile({"style": "chinese"}, "C major", "major", "intermediate")
    voicing = voice_chord("I5", profile, register="left_hand", role="accompaniment")

    intervals = sorted({(pitch - voicing["voicing"][0]) % 12 for pitch in voicing["voicing"]})
    assert 7 in intervals

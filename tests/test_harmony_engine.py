from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.harmony_engine import HarmonyEngine


def test_harmony_engine_adds_final_dominant_tonic_motion() -> None:
    plan = HarmonyEngine().generate(GenerationProfile(style="pop", key="C major"), 8)
    assert plan["progression"] == ["I", "V", "vi", "IV"]
    assert plan["chords"][-2:] == ["V", "I"]

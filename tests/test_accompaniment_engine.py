from backend.generation.musicality.accompaniment_engine import AccompanimentEngine
from backend.generation.musicality.generation_profile import GenerationProfile


def test_accompaniment_engine_defaults_to_left_hand_activity() -> None:
    profile = GenerationProfile(style="classical", difficulty="intermediate", meter="4/4")
    plan = AccompanimentEngine().generate(profile, ["I", "V"])
    assert plan["style"] == "bass_chord"
    assert all(measure["events"] for measure in plan["measures"])


def test_romantic_and_waltz_profiles_choose_expected_styles() -> None:
    engine = AccompanimentEngine()
    assert engine.choose_style(GenerationProfile(style="romantic", accompaniment_style="")) == "arpeggiated_chords"
    assert engine.choose_style(GenerationProfile(meter="3/4", texture="waltz", accompaniment_style="")) == "waltz_bass"

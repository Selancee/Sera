from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.rhythm_engine import RhythmEngine


def test_rhythm_engine_intermediate_output_is_not_only_quarters() -> None:
    profile = GenerationProfile(difficulty="intermediate", rhythmic_density="medium", meter="4/4")

    plan = RhythmEngine().generate(profile, 8)
    labels = [event["label"] for measure in plan["measures"] for event in measure["events"]]

    assert any(label in {"eighth", "sixteenth", "dotted_quarter", "dotted_eighth"} for label in labels)
    assert len({measure["pattern_id"] for measure in plan["measures"]}) >= 3

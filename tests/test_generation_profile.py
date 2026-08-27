from backend.generation.musicality.generation_profile import GenerationProfile
from backend.models.schemas import CompositionPlan, MeasurePlan, StructuredMusicIntent


def test_generation_profile_reads_prompt_keywords_and_controls() -> None:
    intent = StructuredMusicIntent(prompt="需要附点和肖邦感的华尔兹", style="romantic", time_signature="3/4", texture="melody_accompaniment")
    intent.constraints.append("accompaniment_style:alberti_bass")
    plan = CompositionPlan(intent=intent, measures=[MeasurePlan(index=1, section="A", chord="I", function="tonic", rhythm="", density="medium")], global_plan={})
    profile = GenerationProfile.from_plan(plan)
    assert profile.requires_dotted_rhythm is True
    assert profile.rhythmic_density in {"medium", "high"}
    assert profile.texture == "waltz"
    assert profile.accompaniment_style == "alberti_bass"

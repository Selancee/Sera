from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.agents.prompt_understanding_agent import PromptUnderstandingAgent
from backend.generation.musicality.generation_profile import GenerationProfile


def test_generation_profile_preserves_custom_style_tags():
    intent = PromptUnderstandingAgent().understand("Compose a dark cyberpunk piano passage with futuristic energy.")
    plan = CompositionPlanningAgent().plan(intent)
    profile = GenerationProfile.from_plan(plan)

    assert intent.style == "custom"
    assert intent.base_style == "electronic"
    assert "cyberpunk" in intent.custom_style_tags
    assert profile.style == "custom"
    assert profile.base_style == "electronic"
    assert profile.texture == "ostinato"
    assert profile.accompaniment_style == "repeating_bass"
    assert profile.harmony_flavor == "minor_modal"

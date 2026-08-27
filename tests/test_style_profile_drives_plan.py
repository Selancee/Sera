from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.agents.prompt_understanding_agent import PromptUnderstandingAgent


def test_style_profile_changes_measure_plan_texture_and_rhythm() -> None:
    intent = PromptUnderstandingAgent().understand(
        "cyberpunk piano passage, dark futuristic ostinato, syncopated repeated bass, 8 measures"
    )
    plan = CompositionPlanningAgent().plan(intent)

    assert plan.global_plan["texture"] == "ostinato"
    assert plan.global_plan["accompaniment_style"] == "repeating_bass"
    assert plan.global_plan["harmony_flavor"] == "minor_modal"
    assert plan.measures[0].texture == "ostinato"
    assert "ostinato" in plan.measures[0].rhythm
    assert plan.global_plan["plan_grounding"]

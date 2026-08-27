from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.models.schemas import StructuredMusicIntent


def test_composition_plan_prepares_track_roles() -> None:
    intent = StructuredMusicIntent(prompt="Compose an 8 measure piano theme.", instruments=["piano"], bars=8)
    plan = CompositionPlanningAgent().plan(intent)

    assert plan.global_plan["track_plan"]
    assert plan.global_plan["role_coverage_report"]["lead_melody"] is True
    assert "harmony_profile" in plan.global_plan

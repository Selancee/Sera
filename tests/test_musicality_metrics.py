from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.generation.rule_based_generator import RuleBasedGenerator
from backend.models.schemas import StructuredMusicIntent
from evaluation.metrics.musicality_metrics import musicality_metrics_from_musicxml


def test_musicality_metrics_are_stable_numbers() -> None:
    plan = CompositionPlanningAgent().plan(StructuredMusicIntent(prompt="8 bar C major piano", bars=8))
    score = RuleBasedGenerator().generate(plan)
    metrics = musicality_metrics_from_musicxml(score.musicxml)

    assert 0.0 <= metrics["overall_musicality_proxy_score"] <= 1.0
    assert metrics["rhythmic_diversity_score"] > 0.0

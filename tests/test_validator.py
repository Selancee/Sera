from backend.generation.rule_based_generator import RuleBasedGenerator
from backend.agents.prompt_understanding_agent import PromptUnderstandingAgent
from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.validation.musicxml_validator import MusicXMLValidator


def test_musicxml_validator_accepts_rule_based_score() -> None:
    intent = PromptUnderstandingAgent().understand("Create an 8 bar waltz in A minor at 90 bpm.")
    plan = CompositionPlanningAgent().plan(intent)
    score = RuleBasedGenerator().generate(plan)
    result = MusicXMLValidator().validate_text(score.musicxml)

    assert result.valid is True
    assert result.metrics["measure_count"] == 8
    assert result.metrics["bar_completeness"] == 1.0


def test_musicxml_validator_rejects_bad_xml() -> None:
    result = MusicXMLValidator().validate_text("<score-partwise><measure></score-partwise>")

    assert result.valid is False
    assert result.issues

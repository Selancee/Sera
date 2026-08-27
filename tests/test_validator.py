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


def test_musicxml_validator_accepts_complete_rest_only_measure() -> None:
    musicxml = """<?xml version="1.0"?><score-partwise version="3.1"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><rest/><duration>4</duration><voice>1</voice><type>whole</type><staff>1</staff></note></measure></part></score-partwise>"""

    result = MusicXMLValidator().validate_text(musicxml)

    assert result.valid is True
    assert result.metrics["empty_measure_count"] == 0
    assert result.metrics["rest_only_measure_count"] == 1
    assert "No pitched notes found" in result.warnings

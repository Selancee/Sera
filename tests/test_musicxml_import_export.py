from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.generation.rule_based_generator import RuleBasedGenerator
from backend.models.schemas import StructuredMusicIntent
from backend.services.score_document_service import musicxml_to_score_document, score_document_to_musicxml
from backend.validation.musicxml_validator import MusicXMLValidator


def test_musicxml_score_document_roundtrip_validates() -> None:
    plan = CompositionPlanningAgent().plan(StructuredMusicIntent(prompt="8 bar C major piano", bars=8))
    generated = RuleBasedGenerator().generate(plan)

    score_document = musicxml_to_score_document(generated.musicxml)
    exported = score_document_to_musicxml(score_document)
    validation = MusicXMLValidator().validate_text(exported)

    assert score_document["schema_version"] == "0.6"
    assert len(score_document["measures"]) == 8
    assert validation.valid is True


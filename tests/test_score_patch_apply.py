from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.agents.score_editing_agent import ScoreEditingAgent
from backend.generation.rule_based_generator import RuleBasedGenerator
from backend.models.schemas import StructuredMusicIntent
from backend.services.score_document_service import musicxml_to_score_document
from backend.services.score_patch_service import ScorePatchService


def test_score_patch_preview_and_apply_keeps_valid_musicxml() -> None:
    plan = CompositionPlanningAgent().plan(StructuredMusicIntent(prompt="8 bar C major piano", bars=8))
    score = musicxml_to_score_document(RuleBasedGenerator().generate(plan).musicxml)
    patch = ScoreEditingAgent().create_patch(
        score,
        "make the ending more conclusive",
        {"start_measure": 7, "end_measure": 8},
        {},
    )
    service = ScorePatchService()
    preview = service.preview_patch(score, patch, "make the ending more conclusive")
    applied = service.apply_patch(score, patch, "make the ending more conclusive")

    assert preview["validation_report"]["valid_musicxml"] is True
    assert applied["accepted"] is True
    assert applied["score_document"]["measures"][-1]["cadence"] == "authentic"


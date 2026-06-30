from backend.agents.score_editing_agent import ScoreEditingAgent
from backend.services.score_document_service import new_score_document


def test_score_editing_agent_outputs_local_json_patch() -> None:
    patch = ScoreEditingAgent().create_patch(
        new_score_document(measures=8),
        "simplify selected passage",
        {"start_measure": 2, "end_measure": 4},
        {"preserve_form": True},
    )

    assert patch["target_range"] == {"start_measure": 2, "end_measure": 4}
    assert patch["patch_type"] == "simplify"
    assert patch["operations"]
    assert "MusicXML" not in patch


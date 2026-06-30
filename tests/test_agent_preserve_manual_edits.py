from backend.agents.score_editing_agent import ScoreEditingAgent
from backend.services.score_document_service import new_score_document


def test_agent_patch_marks_recent_manual_events_as_excluded() -> None:
    score = new_score_document(measures=2)
    score["measures"][0]["events"].append({"event_id": "n1", "type": "note", "pitch": "C4", "duration": "quarter", "offset": 0, "voice": 1, "staff": "right_hand"})
    patch = ScoreEditingAgent().create_patch(
        score,
        "make selected measures more expressive",
        {"start_measure": 1, "end_measure": 2},
        {"preserve_manual_edits": True},
        edit_context={"recent_operations": [{"source": "user", "target": {"event_id": "n1"}}]},
    )
    assert any("n1" in operation.get("target", {}).get("exclude_event_ids", []) for operation in patch["operations"])


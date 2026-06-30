from fastapi.testclient import TestClient

from backend.app import app
from backend.services.score_document_service import new_score_document


def test_continue_from_last_edit_returns_agent_preview() -> None:
    client = TestClient(app)
    score = new_score_document(measures=2)
    response = client.post(
        "/score/continue_from_last_edit",
        json={
            "score_document": score,
            "selected_range": {"start_measure": 1, "end_measure": 2},
            "recent_operations": [{"source": "user", "type": "update_pitch", "target": {"event_id": "n1"}}],
            "constraints": {"preserve_harmony": True},
        },
    )
    assert response.status_code == 200
    assert response.json()["patch"]["patch_id"]


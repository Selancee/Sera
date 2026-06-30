from fastapi.testclient import TestClient

from backend.app import app
from backend.services.score_operation_service import apply_score_operation, record_operation
from backend.services.score_document_service import new_score_document


def test_revert_last_agent_patch_preserves_later_user_edit() -> None:
    client = TestClient(app)
    score = new_score_document(measures=1)
    history = {"done": [], "undone": []}
    score, agent_op = apply_score_operation(score, {"source": "agent", "type": "insert_note", "target": {"measure": 1}, "after": {"pitch": "C4", "offset": 0}, "description": "agent"})
    history = record_operation(history, agent_op)
    score, user_op = apply_score_operation(score, {"source": "user", "type": "insert_note", "target": {"measure": 1}, "after": {"pitch": "E4", "offset": 1}, "description": "user"})
    history = record_operation(history, user_op)
    response = client.post("/score/revert_last_agent_patch", json={"score_document": score, "operation_history": history, "patch_history": []})
    assert response.status_code == 200
    events = response.json()["score_document"]["measures"][0]["events"]
    assert any(event["pitch"] == "E4" for event in events)


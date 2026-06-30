from fastapi.testclient import TestClient

from backend.app import app
from backend.services.score_document_service import new_score_document


def test_score_batch_operations_applies_multiple_edits() -> None:
    client = TestClient(app)
    score = new_score_document(measures=1)
    response = client.post(
        "/score/batch_operations",
        json={
            "score_document": score,
            "operations": [
                {"source": "user", "type": "insert_note", "target": {"measure": 1}, "after": {"pitch": "C4", "duration": "quarter", "offset": 0}, "description": "insert"},
                {"source": "user", "type": "insert_rest", "target": {"measure": 1}, "after": {"duration": "quarter", "offset": 1}, "description": "rest"},
            ],
            "operation_history": {"done": [], "undone": []},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["operations"]) == 2
    assert len(payload["operation_history"]["done"]) == 2


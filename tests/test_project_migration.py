from fastapi.testclient import TestClient

from backend.app import app
from backend.services.score_document_service import new_score_document


def test_project_migration_endpoint_outputs_v08_project() -> None:
    client = TestClient(app)
    response = client.post("/score/migrate_project", json={"project": {"ScoreDocument": new_score_document(measures=1), "OperationHistory": {"done": [], "undone": []}}})
    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["project_version"] == "0.8"
    assert payload["summary"]["measure_count"] == 1


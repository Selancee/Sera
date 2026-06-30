from fastapi.testclient import TestClient

from backend.app import app
from backend.services.score_document_service import new_score_document


def test_export_project_package_saves_summary() -> None:
    client = TestClient(app)
    response = client.post("/score/export_project_package", json={"project": {"score_document": new_score_document(measures=1), "operation_history": {"done": [], "undone": []}}})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["measure_count"] == 1
    assert payload["path"].endswith("_package.sera.json")

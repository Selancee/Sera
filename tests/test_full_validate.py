from fastapi.testclient import TestClient

from backend.app import app
from backend.services.score_document_service import new_score_document


def test_full_validate_wraps_musicxml_and_light_validation() -> None:
    client = TestClient(app)
    score = new_score_document(measures=1)
    response = client.post("/score/full_validate", json={"score_document": score})
    assert response.status_code == 200
    report = response.json()["validation_report"]
    assert "valid_musicxml" in report
    assert "lightweight" in report


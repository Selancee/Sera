from fastapi.testclient import TestClient

from backend.app import app
from backend.services.score_document_service import new_score_document


def test_light_validate_reports_underfilled_dirty_measure() -> None:
    client = TestClient(app)
    score = new_score_document(measures=1)
    score["measures"][0]["events"].append({"event_id": "n1", "type": "note", "pitch": "C4", "duration": "quarter", "offset": 0, "voice": 1, "staff": "right_hand"})
    response = client.post("/score/light_validate", json={"score_document": score, "dirty_measures": [1]})
    assert response.status_code == 200
    report = response.json()["validation_report"]
    assert report["mode"] == "lightweight"
    assert report["warnings"]


from fastapi.testclient import TestClient

from backend.app import app
from backend.services.score_document_service import new_score_document


def test_generate_accompaniment_returns_previewable_patch() -> None:
    client = TestClient(app)
    score = new_score_document(measures=2)
    response = client.post(
        "/score/generate_accompaniment",
        json={"score_document": score, "selected_range": {"start_measure": 1, "end_measure": 2}, "texture": "arpeggiated"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["patch"]["patch_type"] == "update_texture"
    assert payload["patch"]["operations"]


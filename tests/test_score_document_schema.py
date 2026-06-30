import json
from pathlib import Path

from backend.services.score_document_service import new_score_document


def test_score_document_schema_shape() -> None:
    schema = json.loads(Path("backend/schemas/score_document.schema.json").read_text(encoding="utf-8"))
    score = new_score_document(measures=2)

    assert schema["title"] == "Sera ScoreDocument V0.6"
    assert score["schema_version"] == "0.6"
    assert len(score["measures"]) == 2
    for key in schema["required"]:
        assert key in score


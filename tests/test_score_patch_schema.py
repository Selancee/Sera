import json
from pathlib import Path

from backend.agents.score_editing_agent import ScoreEditingAgent
from backend.services.score_document_service import new_score_document


def test_score_patch_schema_and_mock_patch() -> None:
    schema = json.loads(Path("backend/schemas/score_patch.schema.json").read_text(encoding="utf-8"))
    score = new_score_document(measures=4)
    patch = ScoreEditingAgent().create_patch(
        score,
        "add cadence to the ending",
        {"start_measure": 3, "end_measure": 4},
        {"preserve_form": True},
    )

    assert schema["title"] == "Sera ScorePatch V0.7"
    for key in schema["required"]:
        assert key in patch
    assert patch["patch_type"] == "add_cadence"
    assert patch["operations"][0]["type"] == "add_cadence"

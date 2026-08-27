from backend.services.score_document_service import new_score_document
from backend.services.score_metadata_sync_service import sync_score_metadata_after_resolution


def test_metadata_sync_neutralizes_stale_prompt_key_title() -> None:
    score = new_score_document(title="Classical Sketch in C major", key="A minor", measures=1)
    intent = {
        "title": "Classical Sketch in C major",
        "key": "A minor",
        "instruments": ["piano"],
        "ui_controls": {"key": "A minor"},
        "prompt_ui_conflicts": [{"field": "key", "prompt_value": "C major", "ui_value": "A minor"}],
    }

    result = sync_score_metadata_after_resolution(intent, {"key": "A minor"}, score)

    assert result["score_document"]["title"] == "Sera Piano Sketch"
    assert "C major" not in result["score_document"]["title"]
    assert result["metadata_sync_report"]["stale_key_removed"] is True
    assert result["metadata_sync_report"]["title_sync_status"] == "neutralized"


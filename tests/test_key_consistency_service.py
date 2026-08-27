from backend.services.key_consistency_service import build_key_consistency_report
from backend.services.score_document_service import new_score_document, score_document_to_musicxml


def test_key_consistency_report_detects_stale_title_key() -> None:
    score = new_score_document(title="Classical Sketch in C major", key="A minor", measures=1)
    report = build_key_consistency_report(
        intent={"key": "A minor"},
        resolved_controls={"key": "A minor"},
        score_document=score,
        musicxml=score_document_to_musicxml(score),
    )

    assert report["valid"] is False
    assert report["title_key"] == "C major"
    assert report["stale_key_in_title"] is True


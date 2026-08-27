from backend.services.score_document_service import build_role_coverage_report, new_score_document, normalize_score_document


def test_score_document_supports_optional_tracks() -> None:
    score = new_score_document(measures=1)

    assert score["tracks"][0]["role"] == "lead_melody"
    assert normalize_score_document(score)["tracks"]


def test_existing_piano_score_without_tracks_gets_inferred_tracks() -> None:
    score = new_score_document(measures=1)
    score.pop("tracks", None)
    score["measures"][0]["events"].append(
        {"event_id": "m1_e1", "type": "note", "pitch": "C4", "duration": "quarter", "offset": 0, "voice": 1, "staff": "right_hand"}
    )
    normalized = normalize_score_document(score)

    assert any(track["role"] == "lead_melody" for track in normalized["tracks"])
    assert build_role_coverage_report(normalized)["lead_melody"] is True

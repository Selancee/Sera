from backend.services.score_document_service import duration_to_quarters, new_score_document, normalize_score_document


def test_score_document_keeps_dotted_duration() -> None:
    score = new_score_document(measures=1)
    score["measures"][0]["events"].append(
        {
            "event_id": "m1_e1",
            "type": "note",
            "pitch": "C4",
            "duration": "dotted_quarter",
            "offset": 0,
            "voice": 1,
            "staff": "right_hand",
        }
    )

    normalized = normalize_score_document(score)

    assert normalized["measures"][0]["events"][0]["duration"] == "dotted_quarter"
    assert duration_to_quarters("dotted_quarter") == 1.5

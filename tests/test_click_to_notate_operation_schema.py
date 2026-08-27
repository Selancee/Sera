from backend.services.score_document_service import new_score_document
from backend.services.score_operation_service import apply_score_operation


def test_click_to_notate_insert_note_operation_schema() -> None:
    score = new_score_document(measures=1)
    operation = {
        "type": "insert_note",
        "source": "user",
        "target": {"measure_id": "m1", "staff": "right_hand", "voice": 1, "offset": 1.0},
        "after": {"pitch": "E4", "duration": "dotted_quarter", "dotted": True, "offset": 1.0, "staff": "right_hand", "voice": 1},
    }

    updated, applied = apply_score_operation(score, operation)

    event = updated["measures"][0]["events"][0]
    assert applied["type"] == "insert_note"
    assert event["pitch"] == "E4"
    assert event["duration"] == "dotted_quarter"
    assert event["offset"] == 1.0


def test_click_to_notate_insert_rest_operation_schema() -> None:
    score = new_score_document(measures=1)
    operation = {
        "type": "insert_rest",
        "source": "user",
        "target": {"measure_id": "m1", "staff": "left_hand", "voice": 2, "offset": 0.5},
        "after": {"duration": "dotted_eighth", "dotted": True, "offset": 0.5, "staff": "left_hand", "voice": 2},
    }

    updated, _ = apply_score_operation(score, operation)
    event = updated["measures"][0]["events"][0]

    assert event["type"] == "rest"
    assert event["duration"] == "dotted_eighth"
    assert event["staff"] == "left_hand"
    assert event["voice"] == 2

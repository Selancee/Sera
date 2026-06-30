from backend.services.score_document_service import new_score_document
from backend.services.score_operation_service import apply_score_operation


def test_insert_and_update_note_operation() -> None:
    score = new_score_document(measures=1)
    inserted, insert_op = apply_score_operation(
        score,
        {
            "source": "user",
            "type": "insert_note",
            "target": {"measure": 1},
            "after": {"pitch": "C4", "duration": "quarter", "offset": 0},
            "description": "Insert C4",
        },
    )
    event_id = inserted["measures"][0]["events"][0]["event_id"]
    updated, update_op = apply_score_operation(
        inserted,
        {
            "source": "user",
            "type": "update_pitch",
            "target": {"measure": 1, "event_id": event_id},
            "after": {"pitch": "D4"},
            "description": "Update pitch",
        },
    )

    assert insert_op["before"]["score_document"]["measures"][0]["events"] == []
    assert updated["measures"][0]["events"][0]["pitch"] == "D4"
    assert update_op["after"]["score_document"]["measures"][0]["events"][0]["pitch"] == "D4"


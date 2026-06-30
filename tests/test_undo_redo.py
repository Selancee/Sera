from backend.services.score_document_service import new_score_document
from backend.services.score_operation_service import apply_score_operation, record_operation, redo_last, undo_last


def test_undo_redo_restores_score_document_snapshot() -> None:
    score = new_score_document(measures=1)
    updated, operation = apply_score_operation(
        score,
        {
            "source": "user",
            "type": "insert_note",
            "target": {"measure": 1},
            "after": {"pitch": "E4", "duration": "quarter"},
            "description": "Insert note",
        },
    )
    history = record_operation({"done": [], "undone": []}, operation)

    undone, history = undo_last(updated, history)
    redone, history = redo_last(undone, history)

    assert undone["measures"][0]["events"] == []
    assert redone["measures"][0]["events"][0]["pitch"] == "E4"
    assert len(history["done"]) == 1


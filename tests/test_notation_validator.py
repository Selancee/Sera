from backend.notation.notation_normalizer import normalize_score_document
from backend.notation.notation_validator import validate_score_document_notation


def test_notation_validator_accepts_normalized_4_4_score() -> None:
    score = {
        "schema_version": "0.6",
        "global": {"meter": "4/4"},
        "measures": [
            {
                "measure_id": "m1",
                "number": 1,
                "events": [
                    {"event_id": "n1", "type": "note", "pitch": "C4", "duration": "dotted_quarter", "offset": 0, "voice": 1, "staff": "right_hand"},
                    {"event_id": "n2", "type": "note", "pitch": "D4", "duration": "eighth", "offset": 1.5, "voice": 1, "staff": "right_hand"},
                    {"event_id": "n3", "type": "note", "pitch": "E4", "duration": "half", "offset": 2, "voice": 1, "staff": "right_hand"},
                ],
            }
        ],
    }

    normalized = normalize_score_document(score).score_document
    report = validate_score_document_notation(normalized)

    assert report["valid"] is True
    assert report["measure_duration_valid"] is True
    assert report["dotted_duration_valid"] is True


def test_notation_validator_rejects_overflow_without_normalization() -> None:
    score = {
        "schema_version": "0.6",
        "global": {"meter": "3/4"},
        "measures": [
            {
                "measure_id": "m1",
                "number": 1,
                "events": [{"event_id": "n1", "type": "note", "pitch": "C4", "duration": "whole", "offset": 0, "voice": 1, "staff": "right_hand"}],
            }
        ],
    }

    report = validate_score_document_notation(score)

    assert report["valid"] is False
    assert report["measure_duration_valid"] is False

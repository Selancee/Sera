from backend.notation.notation_normalizer import normalize_score_document


def test_normalizer_fills_empty_measure_with_grouped_rests() -> None:
    score = {"schema_version": "0.6", "global": {"meter": "4/4"}, "measures": [{"measure_id": "m1", "number": 1, "events": []}]}

    result = normalize_score_document(score)

    assert result.score_document["measures"][0]["events"]
    assert result.report["rest_grouping_fixes"] >= 1


def test_normalizer_splits_overlong_note_across_barline_with_tie() -> None:
    score = {
        "schema_version": "0.6",
        "global": {"meter": "4/4"},
        "measures": [
            {
                "measure_id": "m1",
                "number": 1,
                "events": [
                    {
                        "event_id": "n1",
                        "type": "note",
                        "pitch": "C4",
                        "duration": "half",
                        "offset": 3.0,
                        "voice": 1,
                        "staff": "right_hand",
                    }
                ],
            }
        ],
    }

    result = normalize_score_document(score)
    first_measure_note = [event for event in result.score_document["measures"][0]["events"] if event["event_id"] == "n1"][0]
    overflow_note = [event for event in result.score_document["measures"][1]["events"] if event["event_id"] == "n1~tie1"][0]

    assert first_measure_note["duration"] == "quarter"
    assert first_measure_note["tie"] == "start"
    assert overflow_note["tie"] == "stop"
    assert overflow_note["tie_origin_event_id"] == "n1"

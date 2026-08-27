from backend.generation.musicality.melody_expectation_validator import validate_melody_expectation


def test_leap_reversal_gap_fill_and_closure_are_computed() -> None:
    report = validate_melody_expectation(
        [
            {"type": "note", "pitch": "C4", "duration": "eighth", "offset": 0, "measure": 1},
            {"type": "note", "pitch": "G4", "duration": "eighth", "offset": 0.5, "measure": 1},
            {"type": "note", "pitch": "F4", "duration": "eighth", "offset": 1.0, "measure": 1},
            {"type": "note", "pitch": "E4", "duration": "quarter", "offset": 1.5, "measure": 1},
            {"type": "note", "pitch": "C4", "duration": "quarter", "offset": 3.0, "measure": 1},
        ],
        key="C major",
    )

    assert report["leap_reversal_rate"] == 1.0
    assert report["gap_fill_score"] == 1.0
    assert report["closure_score"] > 0.7


def test_unresolved_tritone_is_counted() -> None:
    report = validate_melody_expectation([60, 66, 73], key="C major")

    assert report["unresolved_tritone_count"] >= 1
    assert report["valid"] is False

from backend.generation.musicality.melodic_grammar import validate_cross_measure_melody_events


def test_cross_measure_unresolved_tritone_is_detected() -> None:
    events = [
        {"event_id": "m1e1", "measure_number": 1, "offset": 3.0, "midi": 60},
        {"event_id": "m2e1", "measure_number": 2, "offset": 0.0, "midi": 66},
        {"event_id": "m2e2", "measure_number": 2, "offset": 1.0, "midi": 68},
    ]

    report = validate_cross_measure_melody_events(events, "C major", "major", {}, "intermediate")

    assert report["valid"] is False
    assert report["cross_measure_tritone_rate"] > 0
    assert report["unresolved_cross_measure_leap_count"] == 1


def test_cross_measure_large_leap_is_detected() -> None:
    events = [
        {"event_id": "m1e1", "measure_number": 1, "offset": 3.0, "midi": 60},
        {"event_id": "m2e1", "measure_number": 2, "offset": 0.0, "midi": 74},
    ]

    report = validate_cross_measure_melody_events(events, "C major", "major", {}, "beginner")

    assert report["cross_measure_large_leap_count"] == 1
    assert report["max_cross_measure_interval"] == 14


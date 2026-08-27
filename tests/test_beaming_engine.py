from backend.notation.beaming import assign_beams_to_measure


def test_four_four_beams_eighths_within_quarter_beat() -> None:
    events = [
        {"event_id": "a", "type": "note", "duration": "eighth", "offset": 0.0, "staff": "right_hand", "voice": 1},
        {"event_id": "b", "type": "note", "duration": "eighth", "offset": 0.5, "staff": "right_hand", "voice": 1},
        {"event_id": "c", "type": "note", "duration": "eighth", "offset": 1.0, "staff": "right_hand", "voice": 1},
        {"event_id": "d", "type": "note", "duration": "eighth", "offset": 1.5, "staff": "right_hand", "voice": 1},
    ]

    assigned = assign_beams_to_measure(events, "4/4")

    assert [assigned[0]["beam"]["value"], assigned[1]["beam"]["value"]] == ["begin", "end"]
    assert [assigned[2]["beam"]["value"], assigned[3]["beam"]["value"]] == ["begin", "end"]
    assert assigned[0]["beam_group"] != assigned[2]["beam_group"]


def test_rests_break_beams() -> None:
    events = [
        {"event_id": "a", "type": "note", "duration": "eighth", "offset": 0.0, "staff": "right_hand", "voice": 1},
        {"event_id": "r", "type": "rest", "duration": "eighth", "offset": 0.5, "staff": "right_hand", "voice": 1},
        {"event_id": "b", "type": "note", "duration": "eighth", "offset": 1.0, "staff": "right_hand", "voice": 1},
    ]

    assigned = assign_beams_to_measure(events, "4/4")

    assert "beam" not in assigned[0]
    assert "beam" not in assigned[1]
    assert "beam" not in assigned[2]


def test_six_eight_uses_three_plus_three_eighth_groups() -> None:
    events = [
        {"event_id": f"e{i}", "type": "note", "duration": "eighth", "offset": i * 0.5, "staff": "right_hand", "voice": 1}
        for i in range(6)
    ]

    assigned = assign_beams_to_measure(events, "6/8")

    assert [event["beam"]["value"] for event in assigned[:3]] == ["begin", "continue", "end"]
    assert [event["beam"]["value"] for event in assigned[3:]] == ["begin", "continue", "end"]
    assert assigned[0]["beam_group"] != assigned[3]["beam_group"]

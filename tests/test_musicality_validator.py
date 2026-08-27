from backend.generation.musicality.musicality_validator import validate_musicality


def test_musicality_validator_flags_monophonic_quarter_dominance() -> None:
    score = {
        "measures": [
            {
                "number": index + 1,
                "cadence": "none",
                "events": [
                    {"event_id": f"m{index + 1}_n1", "type": "note", "duration": "quarter", "staff": "right_hand"}
                ],
            }
            for index in range(4)
        ]
    }

    report = validate_musicality(score, {})

    assert report["valid"] is False
    assert report["monophonic_penalty"] == 1.0
    assert report["quarter_note_dominance"] > 0.7

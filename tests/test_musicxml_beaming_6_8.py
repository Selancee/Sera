from backend.services.score_document_service import score_document_to_musicxml


def test_score_document_musicxml_uses_six_eight_three_plus_three_beaming() -> None:
    score = {
        "title": "6/8 beaming",
        "global": {"key": "C major", "meter": "6/8", "tempo": 90},
        "parts": [],
        "measures": [
            {
                "measure_id": "m1",
                "number": 1,
                "section": "A",
                "harmony": "I",
                "cadence": "none",
                "events": [
                    {"event_id": f"m1_e{i}", "type": "note", "pitch": "C5", "duration": "eighth", "offset": i * 0.5, "voice": 1, "staff": "right_hand"}
                    for i in range(6)
                ],
            }
        ],
    }

    musicxml = score_document_to_musicxml(score)

    assert musicxml.count("<beam number=\"1\">begin</beam>") == 2
    assert musicxml.count("<beam number=\"1\">continue</beam>") == 2
    assert musicxml.count("<beam number=\"1\">end</beam>") == 2

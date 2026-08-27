from backend.services.score_document_service import (
    musicxml_to_score_document,
    new_score_document,
    score_document_to_musicxml,
)


def test_musicxml_export_writes_dot_for_dotted_duration() -> None:
    score = new_score_document(measures=1)
    score["measures"][0]["events"].append(
        {
            "event_id": "m1_e1",
            "type": "note",
            "pitch": "C4",
            "duration": "dotted_quarter",
            "offset": 0,
            "voice": 1,
            "staff": "right_hand",
            "tie": None,
            "dynamic": "mf",
            "articulations": [],
            "selected": False,
        }
    )

    musicxml = score_document_to_musicxml(score)

    assert "<type>quarter</type>" in musicxml
    assert "<dot/>" in musicxml


def test_dotted_half_survives_musicxml_roundtrip() -> None:
    score = new_score_document(meter="6/8", measures=1)
    score["measures"][0]["events"].append(
        {
            "event_id": "m1_dotted_half",
            "type": "note",
            "pitch": "C4",
            "duration": "dotted_half",
            "offset": 0,
            "voice": 1,
            "staff": "right_hand",
            "tie": None,
            "dynamic": "mf",
            "articulations": [],
            "selected": False,
        }
    )

    imported = musicxml_to_score_document(score_document_to_musicxml(score))

    assert imported["measures"][0]["events"][0]["duration"] == "dotted_half"

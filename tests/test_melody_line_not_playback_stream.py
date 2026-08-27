from backend.generation.musicality.melody_line_extractor import extract_melody_lines
from backend.services.score_document_service import new_score_document
from backend.services.score_note_event_service import score_document_to_playback_note_events


def test_playback_stream_is_not_primary_melody_diagnostic_stream() -> None:
    score = new_score_document(measures=1)
    score["measures"][0]["events"] = [
        {"event_id": "rh1", "type": "note", "pitch": "C5", "duration": "quarter", "offset": 0.0, "voice": 1, "staff": "right_hand"},
        {"event_id": "lh1", "type": "note", "pitch": "C2", "duration": "quarter", "offset": 0.0, "voice": 1, "staff": "left_hand"},
    ]

    playback = score_document_to_playback_note_events(score)
    melody = extract_melody_lines(score)

    assert {event["diagnostic_stream"] for event in playback} == {"playback_event_stream"}
    assert all(event["melody_diagnostic_eligible"] is False for event in playback)
    assert melody["primary_melody"]["pitches"] == [72]
    assert melody["excluded_lines"][0]["reason"] == "accompaniment"


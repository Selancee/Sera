from backend.generation.musicality.melody_line_extractor import extract_melody_lines
from backend.services.score_document_service import new_score_document


def test_melody_extractor_selects_right_hand_voice_one_and_excludes_left_hand() -> None:
    score = new_score_document(measures=1)
    score["measures"][0]["events"] = [
        {"event_id": "rh1", "type": "note", "pitch": "C5", "duration": "quarter", "offset": 0.0, "voice": 1, "staff": "right_hand"},
        {"event_id": "lh1", "type": "note", "pitch": "C3", "duration": "half", "offset": 0.0, "voice": 1, "staff": "left_hand"},
    ]

    report = extract_melody_lines(score)

    assert report["primary_melody"]["staff"] == "right_hand"
    assert report["primary_melody"]["voice"] == 1
    assert report["primary_melody"]["pitches"] == [72]
    assert report["excluded_lines"][0]["staff"] == "left_hand"


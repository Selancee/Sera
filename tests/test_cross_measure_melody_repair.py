from backend.generation.musicality.melody_line_extractor import extract_melody_lines
from backend.generation.musicality.melodic_grammar import repair_cross_measure_melody, validate_cross_measure_melody_events
from backend.services.score_document_service import new_score_document


def test_cross_measure_repair_reduces_invalid_large_interval() -> None:
    score = new_score_document(measures=2)
    score["measures"][0]["events"] = [
        {"event_id": "m1e1", "type": "note", "pitch": "C4", "duration": "quarter", "offset": 3.0, "voice": 1, "staff": "right_hand"}
    ]
    score["measures"][1]["events"] = [
        {"event_id": "m2e1", "type": "note", "pitch": "D5", "duration": "quarter", "offset": 0.0, "voice": 1, "staff": "right_hand"}
    ]
    melody = extract_melody_lines(score)["primary_melody"]["events"]
    before = validate_cross_measure_melody_events(melody, "C major", "major", {}, "beginner")

    repaired, repair_report = repair_cross_measure_melody(score, melody, "C major", "major", {}, "beginner")
    repaired_melody = extract_melody_lines(repaired)["primary_melody"]["events"]
    after = validate_cross_measure_melody_events(repaired_melody, "C major", "major", {}, "beginner")

    assert before["max_cross_measure_interval"] > after["max_cross_measure_interval"]
    assert repair_report["repairs_applied"]


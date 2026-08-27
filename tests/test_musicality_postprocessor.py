from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.musicality_postprocessor import MusicalityPostprocessor
from backend.services.score_document_service import new_score_document


def test_postprocessor_repairs_monotone_quarter_note_score() -> None:
    score = new_score_document(measures=2)
    for measure in score["measures"]:
        measure["events"] = [
            {"event_id": f"{measure['measure_id']}_e{i}", "type": "note", "pitch": "C4", "duration": "quarter", "offset": float(i), "voice": 1, "staff": "right_hand", "tie": None, "dynamic": "mf", "articulations": [], "selected": False}
            for i in range(4)
        ]
    repaired, report = MusicalityPostprocessor().repair_score_document(score, GenerationProfile())
    assert report["fixed_consecutive_quarters"] is True
    assert report["added_accompaniment"] is True
    assert any(event["staff"] == "left_hand" for measure in repaired["measures"] for event in measure["events"])
    assert repaired["measures"][-1]["cadence"] == "authentic"

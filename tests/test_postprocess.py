from backend.generation.postprocess import postprocess_structured_events


def test_postprocess_reduces_consecutive_quarters() -> None:
    events = ["BAR", "RHYTHM_QUARTER", "NOTE_C4", "RHYTHM_QUARTER", "NOTE_D4", "RHYTHM_QUARTER", "NOTE_E4", "RHYTHM_QUARTER", "NOTE_F4", "RHYTHM_QUARTER", "NOTE_G4", "END"]
    output, report = postprocess_structured_events(events)
    assert report["fixed_consecutive_quarters"] is True
    assert output.count("RHYTHM_QUARTER") < events.count("RHYTHM_QUARTER")

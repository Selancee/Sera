from backend.validation.musicxml_validator import MusicXMLValidator
from training.tokenization.structured_events_to_musicxml import structured_events_to_musicxml


def test_structured_events_to_musicxml_is_parseable() -> None:
    events = [
        "KEY_C_MAJOR",
        "METER_4_4",
        "BAR",
        "POSITION_0",
        "RHYTHM_EIGHTH",
        "NOTE_C4",
        "POSITION_1_2",
        "RHYTHM_EIGHTH",
        "NOTE_D4",
        "POSITION_1",
        "RHYTHM_QUARTER",
        "NOTE_E4",
        "CADENCE_AUTHENTIC",
        "END",
    ]
    musicxml = structured_events_to_musicxml(events)
    result = MusicXMLValidator().validate_text(musicxml)
    assert result.valid is True

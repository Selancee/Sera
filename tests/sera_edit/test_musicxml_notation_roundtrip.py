from __future__ import annotations

from collections import defaultdict
import xml.etree.ElementTree as ET

from backend.services.score_document_service import (
    musicxml_to_score_document,
    new_score_document,
    normalize_score_document,
    score_document_to_musicxml,
)
from backend.validation.musicxml_validator import MusicXMLValidator


def _event(event_id: str, pitch: str, offset: float, **overrides: object) -> dict:
    event = {
        "event_id": event_id,
        "type": "note",
        "pitch": pitch,
        "duration": "quarter",
        "offset": offset,
        "voice": 1,
        "staff": "right_hand",
        "tie": None,
        "slur": None,
        "accidental": "",
        "dynamic": "mf",
        "articulations": [],
        "grace": False,
        "is_chord_tone": False,
        "chord_group_id": None,
        "selected": False,
    }
    event.update(overrides)
    return event


def _by_id(score: dict) -> dict[str, dict]:
    return {
        event["event_id"]: event
        for measure in score["measures"]
        for event in measure["events"]
    }


def test_dynamics_articulations_accidentals_and_relations_roundtrip() -> None:
    score = new_score_document(measures=2)
    score["score_id"] = "score_notation_roundtrip"
    score["measures"][0]["events"] = [
        _event("slur_start", "F#4", 0, dynamic="f", articulations=["staccato", "accent"], accidental="sharp", slur="start"),
        _event("slur_stop", "G4", 1, dynamic="p", articulations=["tenuto"], slur="stop"),
        _event("plain", "A4", 2),
        _event("tie_start", "C5", 3, tie="start"),
    ]
    score["measures"][1]["events"] = [
        _event("tie_stop", "C5", 0, tie="stop"),
        _event("m2_2", "B4", 1),
        _event("m2_3", "A4", 2),
        _event("m2_4", "G4", 3),
    ]
    musicxml = score_document_to_musicxml(normalize_score_document(score))
    imported = musicxml_to_score_document(musicxml)
    events = _by_id(imported)

    assert MusicXMLValidator().validate_text(musicxml).valid is True
    assert events["slur_start"]["dynamic"] == "f"
    assert events["slur_start"]["articulations"] == ["staccato", "accent"]
    assert events["slur_start"]["accidental"] == "sharp"
    assert events["slur_start"]["slur"] == "start"
    assert events["slur_stop"]["slur"] == "stop"
    assert events["tie_start"]["tie"] == "start"
    assert events["tie_stop"]["tie"] == "stop"
    assert events["slur_start"]["pitch"] == "F#4"


def test_export_collapses_persistent_dynamics_and_places_tempo_inside_measure() -> None:
    score = new_score_document(measures=1)
    score["measures"][0]["events"] = [
        *[_event(f"rh_{index}", "C4", index - 1) for index in range(1, 5)],
        *[_event(f"lh_{index}", "C3", index - 1, staff="left_hand") for index in range(1, 5)],
    ]

    musicxml = score_document_to_musicxml(score)
    imported = musicxml_to_score_document(musicxml)
    root = ET.fromstring(musicxml)
    part = root.find("./part")

    assert musicxml.count("<mf/>") == 2
    assert part is not None
    assert [child.tag for child in part][:1] == ["measure"]
    assert part.find("./measure/direction/direction-type/metronome") is not None
    assert all(event["dynamic"] == "mf" for event in _by_id(imported).values())


def test_exported_non_default_dynamic_persists_per_staff_and_voice() -> None:
    score = new_score_document(measures=2)
    score["measures"][0]["events"] = [
        *[_event(f"rh_v1_{index}", "C4", index - 1, dynamic="ff") for index in range(1, 5)],
        *[_event(f"lh_v1_{index}", "C3", index - 1, staff="left_hand", dynamic="ff") for index in range(1, 5)],
        _event("rh_v2_1", "G3", 0, duration="whole", voice=2, dynamic="p"),
    ]
    score["measures"][1]["events"] = [
        *[_event(f"rh_m2_{index}", "D4", index - 1, dynamic="ff") for index in range(1, 5)],
        _event("rh_v2_m2", "A3", 0, duration="whole", voice=2, dynamic="p"),
    ]

    musicxml = score_document_to_musicxml(normalize_score_document(score))
    imported = musicxml_to_score_document(musicxml)
    events = _by_id(imported)

    assert musicxml.count("<ff/>") == 2
    assert musicxml.count("<p/>") == 1
    assert all(events[f"rh_v1_{index}"]["dynamic"] == "ff" for index in range(1, 5))
    assert all(events[f"lh_v1_{index}"]["dynamic"] == "ff" for index in range(1, 5))
    assert all(events[f"rh_m2_{index}"]["dynamic"] == "ff" for index in range(1, 5))
    assert events["rh_v2_1"]["dynamic"] == "p"
    assert events["rh_v2_m2"]["dynamic"] == "p"


def test_chord_membership_and_multiple_voices_roundtrip() -> None:
    score = new_score_document(measures=1)
    score["score_id"] = "score_chord_voice_roundtrip"
    score["measures"][0]["events"] = [
        _event("v1_c", "C4", 0, chord_group_id="chord_1"),
        _event("v1_e", "E4", 0, chord_group_id="chord_1", is_chord_tone=True),
        _event("v1_d", "D4", 1),
        _event("v1_e2", "E4", 2),
        _event("v1_f", "F4", 3),
        _event("v2_c", "C3", 0, duration="whole", voice=2),
    ]
    musicxml = score_document_to_musicxml(normalize_score_document(score))
    imported = musicxml_to_score_document(musicxml)
    events = _by_id(imported)

    assert MusicXMLValidator().validate_text(musicxml).valid is True
    assert musicxml.count("<backup>") >= 1
    assert events["v1_c"]["offset"] == 0
    assert events["v1_e"]["offset"] == 0
    assert events["v1_c"]["chord_group_id"] == "chord_1"
    assert events["v1_e"]["chord_group_id"] == "chord_1"
    assert events["v1_e"]["is_chord_tone"] is True
    assert events["v2_c"]["voice"] == 2
    assert events["v2_c"]["offset"] == 0
    assert events["v2_c"]["duration"] == "whole"


def test_multistaff_export_uses_part_wide_musescore_voice_numbers() -> None:
    score = new_score_document(measures=1)
    score["measures"][0]["events"] = [
        _event("rh_v1", "C4", 0, duration="whole", voice=1),
        _event("rh_v2", "E4", 0, duration="whole", voice=2),
        _event("lh_v1", "C3", 0, duration="whole", voice=1, staff="left_hand"),
        _event("lh_v2", "E3", 0, duration="whole", voice=2, staff="left_hand"),
    ]

    musicxml = score_document_to_musicxml(normalize_score_document(score))
    root = ET.fromstring(musicxml)
    raw_lanes = {
        (
            note.findtext("./pitch/step"),
            note.findtext("./pitch/octave"),
            int(note.findtext("./staff") or 1),
        ): int(note.findtext("./voice") or 1)
        for note in root.findall(".//note")
        if note.find("./pitch") is not None
    }
    imported = _by_id(musicxml_to_score_document(musicxml))

    assert raw_lanes[("C", "4", 1)] == 1
    assert raw_lanes[("E", "4", 1)] == 2
    assert raw_lanes[("C", "3", 2)] == 5
    assert raw_lanes[("E", "3", 2)] == 6
    assert imported["rh_v1"]["voice"] == 1
    assert imported["rh_v2"]["voice"] == 2
    assert imported["lh_v1"]["voice"] == 1
    assert imported["lh_v2"]["voice"] == 2


def test_triplets_and_grace_notes_roundtrip() -> None:
    score = new_score_document(measures=1)
    score["score_id"] = "score_tuplet_grace_roundtrip"
    events = [_event("grace_1", "B3", 0, duration="eighth", grace=True)]
    for index in range(12):
        events.append(
            _event(
                f"triplet_{index + 1}",
                ["C4", "D4", "E4"][index % 3],
                round(index / 3, 6),
                duration="triplet_eighth",
            )
        )
    score["measures"][0]["events"] = events
    musicxml = score_document_to_musicxml(normalize_score_document(score))
    imported = musicxml_to_score_document(musicxml)
    imported_events = _by_id(imported)

    assert MusicXMLValidator().validate_text(musicxml).valid is True
    assert "<divisions>12</divisions>" in musicxml
    assert musicxml.count("<time-modification>") == 12
    assert imported_events["grace_1"]["grace"] is True
    assert imported_events["grace_1"]["offset"] == 0
    assert all(imported_events[f"triplet_{index}"]["duration"] == "triplet_eighth" for index in range(1, 13))


def test_namespaced_external_musicxml_imports_without_losing_note() -> None:
    musicxml = """<?xml version="1.0"?><score-partwise xmlns="http://www.musicxml.org/ns/musicxml" version="4.0"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><pitch><step>E</step><alter>-1</alter><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>whole</type><staff>1</staff><notations><articulations><tenuto/></articulations><dynamics><mp/></dynamics></notations></note></measure></part></score-partwise>"""
    imported = musicxml_to_score_document(musicxml)
    event = imported["measures"][0]["events"][0]
    assert event["pitch"] == "Eb4"
    assert event["duration"] == "whole"
    assert event["dynamic"] == "mp"
    assert event["articulations"] == ["tenuto"]


def test_standard_direction_dynamic_applies_from_mark_position() -> None:
    musicxml = """<?xml version="1.0"?><score-partwise version="3.1"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><direction-type><dynamics><p/></dynamics></direction-type><staff>1</staff></direction><note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>half</type><staff>1</staff></note><direction><direction-type><dynamics><f/></dynamics></direction-type><staff>1</staff></direction><note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>half</type><staff>1</staff></note></measure></part></score-partwise>"""
    imported = musicxml_to_score_document(musicxml)
    assert [event["dynamic"] for event in imported["measures"][0]["events"]] == ["p", "f"]


def test_note_dynamic_overrides_earlier_direction_and_remains_active() -> None:
    musicxml = """<?xml version="1.0"?><score-partwise version="3.1"><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><direction-type><dynamics><p/></dynamics></direction-type><staff>1</staff></direction><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type><staff>1</staff></note><note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>quarter</type><staff>1</staff><notations><dynamics><f/></dynamics></notations></note><note><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>half</type><staff>1</staff></note></measure></part></score-partwise>"""

    imported = musicxml_to_score_document(musicxml)

    assert [event["dynamic"] for event in imported["measures"][0]["events"]] == ["p", "f", "f"]

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET

import pytest

from backend.services.musicxml_source_patch_service import (
    SourcePreservingPatchError,
    patch_musicxml_preserving_source,
)
from backend.services.score_document_service import musicxml_to_score_document
from backend.services.score_document_service import new_score_document, score_document_to_musicxml


LAYOUT_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Layout Source</work-title></work>
  <identification><creator type="composer">Composer</creator></identification>
  <defaults><page-layout><page-height>1683</page-height><page-width>1190</page-width></page-layout></defaults>
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <print new-system="yes"><system-layout><system-distance>120</system-distance></system-layout></print>
      <attributes><divisions>2</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <direction placement="below"><direction-type><dynamics><p/></dynamics></direction-type><staff>1</staff></direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff><beam number="1">begin</beam></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff><beam number="1">end</beam></note>
      <note><rest/><duration>6</duration><voice>1</voice><type>half</type><dot/></note>
    </measure>
    <measure number="2">
      <print new-system="yes"><system-layout><system-distance>140</system-distance></system-layout></print>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>8</duration><voice>1</voice><type>whole</type><staff>1</staff></note>
    </measure>
  </part>
</score-partwise>
"""


def _count(root: ET.Element, path: str) -> int:
    return len(root.findall(path))


def test_pitch_patch_preserves_layout_dynamics_rests_and_non_target_measure() -> None:
    before = musicxml_to_score_document(LAYOUT_MUSICXML, source="musescore_bridge")
    after = copy.deepcopy(before)
    after["measures"][0]["events"][0]["pitch"] = "D4"
    source_root = ET.fromstring(LAYOUT_MUSICXML)
    source_measure_2 = ET.tostring(source_root.findall(".//measure")[1], encoding="unicode")

    result = patch_musicxml_preserving_source(LAYOUT_MUSICXML, before, after)

    patched_root = ET.fromstring(result["musicxml"])
    assert result["export_mode"] == "source_preserving_patch"
    assert result["changed_event_count"] == 1
    assert result["changed_fields"] == ["pitch"]
    assert patched_root.findtext(".//measure[@number='1']/note[1]/pitch/step") == "D"
    assert _count(patched_root, ".//note") == _count(source_root, ".//note")
    assert _count(patched_root, ".//note/rest") == _count(source_root, ".//note/rest")
    assert _count(patched_root, ".//direction/direction-type/dynamics/*") == 1
    assert _count(patched_root, ".//note/notations/dynamics/*") == 0
    assert _count(patched_root, ".//defaults") == 1
    assert _count(patched_root, ".//print") == 2
    assert ET.tostring(patched_root.findall(".//measure")[1], encoding="unicode") == source_measure_2


def test_source_patch_updates_title_without_rebuilding_score() -> None:
    before = musicxml_to_score_document(LAYOUT_MUSICXML, source="musescore_bridge")
    after = copy.deepcopy(before)
    after["title"] = "Edited by Sera"

    result = patch_musicxml_preserving_source(LAYOUT_MUSICXML, before, after)

    root = ET.fromstring(result["musicxml"])
    assert root.findtext(".//work-title") == "Edited by Sera"
    assert len(root.findall(".//note")) == 4
    assert len(root.findall(".//print")) == 2


def test_source_patch_updates_initial_key_without_transposing_or_rebuilding_score() -> None:
    before = musicxml_to_score_document(LAYOUT_MUSICXML, source="musescore_bridge")
    after = copy.deepcopy(before)
    after["global"]["key"] = "G major"
    source_root = ET.fromstring(LAYOUT_MUSICXML)
    source_pitches = [
        (note.findtext("./pitch/step"), note.findtext("./pitch/alter"), note.findtext("./pitch/octave"))
        for note in source_root.findall(".//note")
    ]
    source_measure_2 = ET.tostring(source_root.findall(".//measure")[1], encoding="unicode")

    result = patch_musicxml_preserving_source(LAYOUT_MUSICXML, before, after)

    patched_root = ET.fromstring(result["musicxml"])
    reparsed = musicxml_to_score_document(result["musicxml"], source="musescore_bridge")
    patched_pitches = [
        (note.findtext("./pitch/step"), note.findtext("./pitch/alter"), note.findtext("./pitch/octave"))
        for note in patched_root.findall(".//note")
    ]
    assert result["export_mode"] == "source_preserving_global_patch"
    assert result["changed_event_count"] == 0
    assert result["changed_fields"] == ["key"]
    assert result["changed_global_fields"] == ["key"]
    assert patched_root.findtext(".//part/measure[1]/attributes/key/fifths") == "1"
    assert patched_root.findtext(".//part/measure[1]/attributes/key/mode") == "major"
    assert reparsed["global"]["key"] == "G major"
    assert patched_pitches == source_pitches
    assert _count(patched_root, ".//defaults") == 1
    assert _count(patched_root, ".//print") == 2
    assert ET.tostring(patched_root.findall(".//measure")[1], encoding="unicode") == source_measure_2


def test_source_patch_updates_displayed_meter_without_rebuilding_score() -> None:
    before = musicxml_to_score_document(LAYOUT_MUSICXML, source="musescore_bridge")
    after = copy.deepcopy(before)
    after["global"]["meter"] = "2/2"

    result = patch_musicxml_preserving_source(LAYOUT_MUSICXML, before, after)

    root = ET.fromstring(result["musicxml"])
    reparsed = musicxml_to_score_document(result["musicxml"], source="musescore_bridge")
    assert result["export_mode"] == "source_preserving_global_patch"
    assert result["changed_global_fields"] == ["meter"]
    assert root.findtext(".//part/measure[1]/attributes/time/beats") == "2"
    assert root.findtext(".//part/measure[1]/attributes/time/beat-type") == "2"
    assert reparsed["global"]["meter"] == "2/2"
    assert _count(root, ".//note") == 4


def test_source_patch_preserves_mid_measure_local_key_change() -> None:
    source = LAYOUT_MUSICXML.replace(
        "      <note><pitch><step>D</step>",
        "      <attributes><key><fifths>-1</fifths><mode>major</mode></key></attributes>\n"
        "      <note><pitch><step>D</step>",
        1,
    )
    before = musicxml_to_score_document(source, source="musescore_bridge")
    after = copy.deepcopy(before)
    after["global"]["key"] = "G major"

    result = patch_musicxml_preserving_source(source, before, after)

    root = ET.fromstring(result["musicxml"])
    assert [node.text for node in root.findall(".//measure[@number='1']/attributes/key/fifths")] == ["1", "-1"]


def test_source_patch_replaces_one_note_with_a_chord_without_rebuilding_measure() -> None:
    before = musicxml_to_score_document(LAYOUT_MUSICXML, source="musescore_bridge")
    after = copy.deepcopy(before)
    anchor = after["measures"][0]["events"].pop(0)
    for index, pitch in enumerate(("C4", "E4", "G4"), start=1):
        event = copy.deepcopy(anchor)
        event["event_id"] = f"replacement_chord_{index}"
        event["pitch"] = pitch
        event["is_chord_tone"] = index > 1
        event["chord_group_id"] = "replacement_chord"
        after["measures"][0]["events"].append(event)

    result = patch_musicxml_preserving_source(LAYOUT_MUSICXML, before, after)

    patched_root = ET.fromstring(result["musicxml"])
    reparsed = musicxml_to_score_document(result["musicxml"], source="musescore_bridge")
    chord = [
        event
        for event in reparsed["measures"][0]["events"]
        if event.get("chord_group_id") == "replacement_chord"
    ]
    assert result["export_mode"] == "source_preserving_structural_patch"
    assert result["changed_event_count"] == 4
    assert result["changed_fields"] == ["event_deleted", "event_inserted"]
    assert [event["pitch"] for event in chord] == ["C4", "E4", "G4"]
    assert [event["is_chord_tone"] for event in chord] == [False, True, True]
    assert [event.get("beam") for event in chord] == [
        {"number": 1, "value": "begin"},
        {"number": 1, "value": "begin"},
        {"number": 1, "value": "begin"},
    ]
    assert _count(patched_root, ".//defaults") == 1
    assert _count(patched_root, ".//print") == 2
    assert _count(patched_root, ".//direction/direction-type/dynamics/*") == 1
    assert _count(patched_root, ".//measure[@number='2']/note") == 1


def test_source_patch_merges_duration_and_deletes_event_without_rebuilding_measure() -> None:
    before = musicxml_to_score_document(LAYOUT_MUSICXML, source="musescore_bridge")
    after = copy.deepcopy(before)
    after["measures"][0]["events"][0]["duration"] = "quarter"
    deleted_id = after["measures"][0]["events"].pop(1)["event_id"]

    result = patch_musicxml_preserving_source(LAYOUT_MUSICXML, before, after)

    root = ET.fromstring(result["musicxml"])
    reparsed = musicxml_to_score_document(result["musicxml"], source="musescore_bridge")
    assert result["export_mode"] == "source_preserving_structural_patch"
    assert deleted_id not in {
        event["event_id"]
        for measure in reparsed["measures"]
        for event in measure["events"]
    }
    assert root.findtext(".//measure[@number='1']/note[1]/duration") == "2"
    assert root.findtext(".//measure[@number='1']/note[1]/type") == "quarter"
    assert _count(root, ".//note") == 3


def test_source_patch_updates_voice_and_slur_relations_in_place() -> None:
    before = musicxml_to_score_document(LAYOUT_MUSICXML, source="musescore_bridge")
    after = copy.deepcopy(before)
    first, second = after["measures"][0]["events"][:2]
    first["voice"] = 2
    second["voice"] = 2
    first["slur"] = "start"
    second["slur"] = "stop"

    result = patch_musicxml_preserving_source(LAYOUT_MUSICXML, before, after)

    root = ET.fromstring(result["musicxml"])
    reparsed = musicxml_to_score_document(result["musicxml"], source="musescore_bridge")
    assert [root.findtext(f".//measure[@number='1']/note[{index}]/voice") for index in (1, 2)] == ["2", "2"]
    assert root.find(".//measure[@number='1']/note[1]/notations/slur[@type='start']") is not None
    assert root.find(".//measure[@number='1']/note[2]/notations/slur[@type='stop']") is not None
    events_by_pitch = {
        event.get("pitch"): event
        for event in reparsed["measures"][0]["events"]
        if event.get("type") == "note"
    }
    assert (events_by_pitch["C4"]["voice"], events_by_pitch["C4"]["slur"]) == (2, "start")
    assert (events_by_pitch["D4"]["voice"], events_by_pitch["D4"]["slur"]) == (2, "stop")


def test_voice_patch_normalizes_legacy_lower_staff_lanes_without_changing_their_semantics() -> None:
    score = new_score_document(measures=3)
    for measure_number, measure in enumerate(score["measures"], start=1):
        measure["events"] = [
            {
                "event_id": f"m{measure_number}_rh_v1",
                "type": "note",
                "pitch": "C4",
                "duration": "whole",
                "offset": 0,
                "voice": 1,
                "staff": "right_hand",
            },
            {
                "event_id": f"m{measure_number}_lh_v1",
                "type": "note",
                "pitch": "C3",
                "duration": "whole",
                "offset": 0,
                "voice": 1,
                "staff": "left_hand",
            },
            {
                "event_id": f"m{measure_number}_lh_v2",
                "type": "note",
                "pitch": "E3",
                "duration": "whole",
                "offset": 0,
                "voice": 2,
                "staff": "left_hand",
            },
        ]
    host_safe_source = score_document_to_musicxml(score)
    legacy_source = host_safe_source.replace("<voice>5</voice>", "<voice>1</voice>").replace(
        "<voice>6</voice>", "<voice>2</voice>"
    )
    before = musicxml_to_score_document(legacy_source, source="legacy_sera")
    after = copy.deepcopy(before)
    target = next(
        event
        for event in after["measures"][2]["events"]
        if event["event_id"] == "m3_rh_v1"
    )
    target["voice"] = 2

    result = patch_musicxml_preserving_source(legacy_source, before, after)
    root = ET.fromstring(result["musicxml"])
    reparsed = musicxml_to_score_document(result["musicxml"], source="musescore_bridge")
    reparsed_by_id = {
        event["event_id"]: event
        for measure in reparsed["measures"]
        for event in measure["events"]
    }
    raw_staff_voices = [
        (int(note.findtext("./staff") or 1), int(note.findtext("./voice") or 1))
        for note in root.findall(".//note")
        if note.find("./pitch") is not None
    ]

    assert result["normalized_host_voice_count"] == 6
    assert raw_staff_voices.count((1, 1)) == 2
    assert raw_staff_voices.count((1, 2)) == 1
    assert raw_staff_voices.count((2, 5)) == 3
    assert raw_staff_voices.count((2, 6)) == 3
    assert reparsed_by_id["m3_rh_v1"]["voice"] == 2
    assert all(reparsed_by_id[f"m{measure}_lh_v1"]["voice"] == 1 for measure in range(1, 4))
    assert all(reparsed_by_id[f"m{measure}_lh_v2"]["voice"] == 2 for measure in range(1, 4))


def test_source_patch_restores_persistent_dynamic_after_one_target_note() -> None:
    before = musicxml_to_score_document(LAYOUT_MUSICXML, source="musescore_bridge")
    after = copy.deepcopy(before)
    after["measures"][0]["events"][0]["dynamic"] = "f"

    result = patch_musicxml_preserving_source(LAYOUT_MUSICXML, before, after)

    root = ET.fromstring(result["musicxml"])
    reparsed = musicxml_to_score_document(result["musicxml"], source="musescore_bridge")
    assert root.find(".//measure[@number='1']/note[1]/notations/dynamics/f") is not None
    assert root.find(".//measure[@number='1']/note[2]/notations/dynamics/p") is not None
    notes = [event for event in reparsed["measures"][0]["events"] if event.get("type") == "note"]
    assert [(event["pitch"], event["dynamic"]) for event in notes] == [("C4", "f"), ("D4", "p")]

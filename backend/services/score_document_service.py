"""Canonical ScoreDocument helpers for Sera V0.6.

MusicXML stays an import/export format.  The workbench edits this compact
ScoreDocument shape and converts it back to MusicXML, MIDI events, or project
JSON when needed.
"""

from __future__ import annotations

import copy
import json
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from evaluation.analysis.music_statistics import parse_musicxml_notes, parse_pitch_name


DURATION_TO_QUARTERS = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "sixteenth": 0.25,
    "dotted_quarter": 1.5,
    "dotted eighth": 0.75,
    "dotted_eighth": 0.75,
    "dotted_half": 3.0,
    "triplet_eighth": 1.0 / 3.0,
}
QUARTERS_TO_DURATION = {
    4.0: "whole",
    2.0: "half",
    1.5: "dotted_quarter",
    1.0: "quarter",
    0.75: "dotted_eighth",
    0.5: "eighth",
    0.25: "sixteenth",
}
STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SEMITONE_TO_STEP = {
    0: ("C", 0),
    1: ("C", 1),
    2: ("D", 0),
    3: ("E", -1),
    4: ("E", 0),
    5: ("F", 0),
    6: ("F", 1),
    7: ("G", 0),
    8: ("A", -1),
    9: ("A", 0),
    10: ("B", -1),
    11: ("B", 0),
}


def utc_now() -> str:
    """Return an ISO timestamp for project and operation metadata."""

    return datetime.now(UTC).isoformat()


def new_score_document(
    title: str = "Untitled Sera Score",
    prompt: str = "",
    key: str = "C major",
    meter: str = "4/4",
    tempo: int = 90,
    measures: int = 4,
) -> dict[str, Any]:
    """Create an empty but valid V0.6 ScoreDocument."""

    stamp = utc_now()
    return {
        "schema_version": "0.6",
        "score_id": f"score_{uuid.uuid4().hex[:12]}",
        "title": title,
        "composer": "Sera",
        "metadata": {
            "created_at": stamp,
            "updated_at": stamp,
            "source": "generated" if prompt else "edited",
            "prompt": prompt,
            "agent_plan_id": "",
        },
        "global": {"key": key, "meter": meter, "tempo": int(tempo), "pickup": False},
        "parts": [
            {
                "part_id": "piano",
                "name": "Piano",
                "instrument": "piano",
                "staves": [
                    {"staff_id": "right_hand", "clef": "treble", "measures": [f"m{i}" for i in range(1, measures + 1)]},
                    {"staff_id": "left_hand", "clef": "bass", "measures": [f"m{i}" for i in range(1, measures + 1)]},
                ],
            }
        ],
        "measures": [
            {
                "measure_id": f"m{i}",
                "number": i,
                "section": "A",
                "harmony": "I",
                "cadence": "none",
                "events": [],
            }
            for i in range(1, measures + 1)
        ],
        "annotations": [],
    }


def musicxml_to_score_document(musicxml: str, prompt: str = "", source: str = "imported") -> dict[str, Any]:
    """Convert MusicXML text into a canonical V0.6 ScoreDocument."""

    root = ET.fromstring(musicxml)
    title = root.findtext(".//work-title") or "Imported Sera Score"
    key, meter, tempo = _global_from_musicxml(root)
    measure_nodes = root.findall(".//measure")
    measure_count = max(1, len(measure_nodes))
    score = new_score_document(title=title, prompt=prompt, key=key, meter=meter, tempo=tempo, measures=measure_count)
    score["metadata"]["source"] = source
    measure_meta = _measure_labels_from_musicxml(root)
    by_measure: dict[int, list[dict[str, Any]]] = {i: [] for i in range(1, measure_count + 1)}
    for index, note in enumerate(parse_musicxml_notes(musicxml), start=1):
        duration = _duration_label(note.duration_quarter, note.dotted)
        staff = "left_hand" if str(note.staff) == "2" else "right_hand"
        event = {
            "event_id": f"m{note.measure}_e{index}",
            "type": "rest" if note.is_rest else "note",
            "pitch": "" if note.is_rest else note.pitch,
            "duration": duration,
            "offset": float(note.offset_quarter),
            "voice": int(note.voice) if str(note.voice).isdigit() else 1,
            "staff": staff,
            "tie": None,
            "dynamic": "mf",
            "articulations": [],
            "selected": False,
        }
        by_measure.setdefault(note.measure, []).append(event)
    for measure in score["measures"]:
        number = int(measure["number"])
        labels = measure_meta.get(number, {})
        measure["section"] = labels.get("section", measure["section"])
        measure["harmony"] = labels.get("harmony", measure["harmony"])
        measure["events"] = sorted(by_measure.get(number, []), key=lambda item: (item["staff"], item["offset"], item["voice"]))
    return normalize_score_document(score)


def score_document_to_musicxml(score: dict[str, Any]) -> str:
    """Export a ScoreDocument to parseable MusicXML."""

    score = normalize_score_document(score)
    global_info = score.get("global", {})
    key = str(global_info.get("key", "C major"))
    meter = str(global_info.get("meter", "4/4"))
    tempo = int(global_info.get("tempo", 90))
    beats, beat_type = _parse_meter(meter)
    divisions = 4
    expected = int(beats * divisions * (4 / beat_type))
    measures = score.get("measures") or []
    measure_xml = [
        _measure_to_xml(measure, key, beats, beat_type, divisions, expected, first=index == 0)
        for index, measure in enumerate(measures)
    ]
    title = escape(str(score.get("title") or "Sera Workbench Score"))
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
            '<score-partwise version="3.1">',
            "  <work>",
            f"    <work-title>{title}</work-title>",
            "  </work>",
            "  <identification>",
            "    <creator type=\"composer\">Sera Score Workbench V0.6</creator>",
            "  </identification>",
            "  <part-list>",
            "    <score-part id=\"P1\"><part-name>Piano</part-name></score-part>",
            "  </part-list>",
            "  <part id=\"P1\">",
            f"    <direction placement=\"above\"><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>{tempo}</per-minute></metronome></direction-type></direction>",
            *measure_xml,
            "  </part>",
            "</score-partwise>",
            "",
        ]
    )


def score_document_to_note_events(score: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a ScoreDocument into MIDI exporter note events."""

    score = normalize_score_document(score)
    beats, beat_type = _parse_meter(str(score.get("global", {}).get("meter", "4/4")))
    measure_quarters = beats * (4 / beat_type)
    events: list[dict[str, Any]] = []
    for measure in score.get("measures", []):
        measure_number = int(measure.get("number", 1))
        base = (measure_number - 1) * measure_quarters
        for event in measure.get("events", []):
            if event.get("type") == "rest":
                continue
            midi = parse_pitch_name(str(event.get("pitch", "")))
            if midi is None:
                continue
            events.append(
                {
                    "measure": measure_number,
                    "pitch": event.get("pitch"),
                    "midi": midi,
                    "start_quarter": base + float(event.get("offset", 0.0)),
                    "duration_quarter": duration_to_quarters(str(event.get("duration", "quarter"))),
                    "velocity": _dynamic_velocity(str(event.get("dynamic", "mf"))),
                    "voice": int(event.get("voice", 1) or 1),
                    "staff": 2 if event.get("staff") == "left_hand" else 1,
                }
            )
    return events


def normalize_score_document(score: dict[str, Any]) -> dict[str, Any]:
    """Fill missing ScoreDocument fields without mutating the caller's object."""

    normalized = copy.deepcopy(score or {})
    template = new_score_document(measures=max(1, len(normalized.get("measures") or [])))
    for key, value in template.items():
        normalized.setdefault(key, value)
    normalized["schema_version"] = "0.6"
    normalized.setdefault("metadata", {})
    normalized.setdefault("global", {})
    normalized["metadata"].setdefault("created_at", utc_now())
    normalized["metadata"]["updated_at"] = utc_now()
    normalized["metadata"].setdefault("source", "edited")
    normalized["metadata"].setdefault("prompt", "")
    normalized["metadata"].setdefault("agent_plan_id", "")
    normalized["global"].setdefault("key", "C major")
    normalized["global"].setdefault("meter", "4/4")
    normalized["global"].setdefault("tempo", 90)
    normalized["global"].setdefault("pickup", False)
    normalized.setdefault("parts", template["parts"])
    normalized.setdefault("annotations", [])
    measures = normalized.get("measures") or template["measures"]
    for index, measure in enumerate(measures, start=1):
        measure.setdefault("measure_id", f"m{index}")
        measure.setdefault("number", index)
        measure.setdefault("section", "A")
        measure.setdefault("harmony", "I")
        measure.setdefault("cadence", "none")
        measure.setdefault("events", [])
        for event_index, event in enumerate(measure["events"], start=1):
            event.setdefault("event_id", f"{measure['measure_id']}_e{event_index}")
            event.setdefault("type", "note")
            event.setdefault("pitch", "C4" if event["type"] != "rest" else "")
            event.setdefault("duration", "quarter")
            event.setdefault("offset", 0.0)
            event.setdefault("voice", 1)
            event.setdefault("staff", "right_hand")
            event.setdefault("tie", None)
            event.setdefault("slur", None)
            event.setdefault("accidental", "")
            event.setdefault("dynamic", "mf")
            event.setdefault("articulations", [])
            event.setdefault("selected", False)
    normalized["measures"] = measures
    return normalized


def save_score_project(path: str | Path, payload: dict[str, Any]) -> Path:
    """Persist a self-contained .sera.json project file."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_score_project(path: str | Path) -> dict[str, Any]:
    """Load a .sera.json project file."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def duration_to_quarters(duration: str) -> float:
    """Return quarter-note units for a workbench duration label."""

    return float(DURATION_TO_QUARTERS.get(duration.replace("-", "_"), 1.0))


def midi_to_pitch(midi: int) -> str:
    """Return a pitch label from MIDI."""

    octave = midi // 12 - 1
    step, alter = SEMITONE_TO_STEP[midi % 12]
    accidental = "#" if alter > 0 else "b" if alter < 0 else ""
    return f"{step}{accidental}{octave}"


def transpose_pitch(pitch: str, semitones: int) -> str:
    """Transpose one compact pitch name by semitones."""

    midi = parse_pitch_name(pitch)
    if midi is None:
        return pitch
    return midi_to_pitch(max(21, min(108, midi + semitones)))


def _measure_to_xml(
    measure: dict[str, Any],
    key: str,
    beats: int,
    beat_type: int,
    divisions: int,
    expected: int,
    first: bool,
) -> str:
    right = [event for event in measure.get("events", []) if event.get("staff", "right_hand") != "left_hand"]
    left = [event for event in measure.get("events", []) if event.get("staff") == "left_hand"]
    lines = [f'      <measure number="{int(measure.get("number", 1))}">']
    if first:
        lines.extend(_attributes_xml(key, beats, beat_type, divisions))
    lines.append(
        f"        <direction placement=\"above\"><direction-type><words>{escape(str(measure.get('section', 'A')))} {escape(str(measure.get('harmony', 'I')))}</words></direction-type></direction>"
    )
    lines.extend(_staff_events_to_xml(right, expected, divisions, staff_number=1))
    if left:
        lines.append("        <backup>")
        lines.append(f"          <duration>{expected}</duration>")
        lines.append("        </backup>")
        lines.extend(_staff_events_to_xml(left, expected, divisions, staff_number=2))
    lines.append("      </measure>")
    return "\n".join(lines)


def _staff_events_to_xml(events: list[dict[str, Any]], expected: int, divisions: int, staff_number: int) -> list[str]:
    lines: list[str] = []
    cursor = 0
    for event in sorted(events, key=lambda item: (float(item.get("offset", 0.0)), int(item.get("voice", 1) or 1))):
        offset = max(0, int(round(float(event.get("offset", 0.0)) * divisions)))
        if offset > cursor:
            lines.extend(_rest_xml(offset - cursor, staff_number))
            cursor = offset
        duration = max(1, int(round(duration_to_quarters(str(event.get("duration", "quarter"))) * divisions)))
        duration = min(duration, max(1, expected - cursor))
        if event.get("type") == "rest":
            lines.extend(_rest_xml(duration, staff_number, event))
        else:
            lines.extend(_note_xml(str(event.get("pitch", "C4")), duration, staff_number, int(event.get("voice", 1) or 1), event))
        cursor += duration
        if cursor >= expected:
            break
    if cursor < expected:
        lines.extend(_rest_xml(expected - cursor, staff_number))
    return lines


def _note_xml(pitch: str, duration: int, staff_number: int, voice: int, event: dict[str, Any] | None = None) -> list[str]:
    midi = parse_pitch_name(pitch) or 60
    step, alter = SEMITONE_TO_STEP[midi % 12]
    octave = midi // 12 - 1
    note_type, dotted = _duration_type(duration)
    lines = [
        f"        <!-- sera-event-id:{escape(str((event or {}).get('event_id', '')))} -->",
        "        <note>",
        "          <pitch>",
        f"            <step>{step}</step>",
    ]
    if alter:
        lines.append(f"            <alter>{alter}</alter>")
    lines.extend(
        [
            f"            <octave>{octave}</octave>",
            "          </pitch>",
            f"          <duration>{duration}</duration>",
            f"          <voice>{voice}</voice>",
            f"          <type>{note_type}</type>",
        ]
    )
    if dotted:
        lines.append("          <dot/>")
    lines.append(f"          <staff>{staff_number}</staff>")
    if event is not None:
        lines.append(f"          <notations><technical><other-technical>sera-event-id:{escape(str(event.get('event_id', '')))}</other-technical></technical></notations>")
    lines.append("        </note>")
    return lines


def _rest_xml(duration: int, staff_number: int, event: dict[str, Any] | None = None) -> list[str]:
    note_type, dotted = _duration_type(duration)
    lines = [
        f"        <!-- sera-event-id:{escape(str((event or {}).get('event_id', 'auto-rest')))} -->",
        "        <note>",
        "          <rest/>",
        f"          <duration>{duration}</duration>",
        "          <voice>1</voice>",
        f"          <type>{note_type}</type>",
    ]
    if dotted:
        lines.append("          <dot/>")
    lines.append(f"          <staff>{staff_number}</staff>")
    if event is not None:
        lines.append(f"          <notations><technical><other-technical>sera-event-id:{escape(str(event.get('event_id', '')))}</other-technical></technical></notations>")
    lines.append("        </note>")
    return lines


def _attributes_xml(key: str, beats: int, beat_type: int, divisions: int) -> list[str]:
    return [
        "        <attributes>",
        f"          <divisions>{divisions}</divisions>",
        "          <key>",
        f"            <fifths>{_key_fifths(key)}</fifths>",
        f"            <mode>{'minor' if 'minor' in key.lower() else 'major'}</mode>",
        "          </key>",
        "          <time>",
        f"            <beats>{beats}</beats>",
        f"            <beat-type>{beat_type}</beat-type>",
        "          </time>",
        "          <staves>2</staves>",
        "          <clef number=\"1\"><sign>G</sign><line>2</line></clef>",
        "          <clef number=\"2\"><sign>F</sign><line>4</line></clef>",
        "        </attributes>",
    ]


def _duration_type(duration: int) -> tuple[str, bool]:
    mapping = {
        1: ("16th", False),
        2: ("eighth", False),
        3: ("eighth", True),
        4: ("quarter", False),
        6: ("quarter", True),
        12: ("half", True),
        8: ("half", False),
        16: ("whole", False),
    }
    return mapping.get(duration, ("quarter", False))


def _duration_label(duration_quarter: float, dotted: bool = False) -> str:
    if dotted and abs(duration_quarter - 0.75) < 0.02:
        return "dotted_eighth"
    if dotted or abs(duration_quarter - 1.5) < 0.02:
        return "dotted_quarter"
    return QUARTERS_TO_DURATION.get(round(float(duration_quarter), 2), "quarter")


def _global_from_musicxml(root: ET.Element) -> tuple[str, str, int]:
    attr = root.find(".//attributes")
    fifths = 0
    mode = "major"
    beats = "4"
    beat_type = "4"
    if attr is not None:
        fifths = _int_text(attr.find("./key/fifths"), 0)
        mode = attr.findtext("./key/mode") or "major"
        beats = attr.findtext("./time/beats") or "4"
        beat_type = attr.findtext("./time/beat-type") or "4"
    key = _key_from_fifths(fifths, mode)
    tempo_node = root.find(".//per-minute")
    tempo = _int_text(tempo_node, 90)
    return key, f"{beats}/{beat_type}", tempo


def _measure_labels_from_musicxml(root: ET.Element) -> dict[int, dict[str, str]]:
    labels: dict[int, dict[str, str]] = {}
    for index, measure in enumerate(root.findall(".//measure"), start=1):
        number = int(measure.get("number") or index)
        words = " ".join((node.text or "").strip() for node in measure.findall(".//words") if (node.text or "").strip())
        if words:
            parts = words.split()
            labels[number] = {"section": parts[0], "harmony": parts[1] if len(parts) > 1 else "I"}
    return labels


def _parse_meter(meter: str) -> tuple[int, int]:
    try:
        beats, beat_type = meter.split("/")
        return int(beats), int(beat_type)
    except (ValueError, AttributeError):
        return 4, 4


def _key_fifths(key: str) -> int:
    tonic = key.split()[0].replace("-flat", "b")
    fifths = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "F": -1, "Bb": -2, "Eb": -3, "Ab": -4, "Db": -5}
    value = fifths.get(tonic, 0)
    return value - 3 if "minor" in key.lower() else value


def _key_from_fifths(fifths: int, mode: str) -> str:
    major = {0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", -1: "F", -2: "Bb", -3: "Eb", -4: "Ab", -5: "Db"}
    if mode.lower() == "minor":
        tonic = major.get(fifths + 3, "A")
        return f"{tonic} minor"
    return f"{major.get(fifths, 'C')} major"


def _int_text(node: ET.Element | None, fallback: int) -> int:
    if node is None or node.text is None:
        return fallback
    try:
        return int(float(node.text.strip()))
    except ValueError:
        return fallback


def _dynamic_velocity(dynamic: str) -> int:
    return {"p": 48, "mp": 60, "mf": 76, "f": 92}.get(dynamic, 76)

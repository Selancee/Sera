"""Canonical ScoreDocument helpers for Sera V0.6.

MusicXML stays an import/export format.  The workbench edits this compact
ScoreDocument shape and converts it back to MusicXML, MIDI events, or project
JSON when needed.
"""

from __future__ import annotations

import copy
import json
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from fractions import Fraction
from html import escape
from pathlib import Path
from typing import Any

from backend.notation.beaming import materialize_beams_for_score_document
from backend.services.musicxml_voice_service import (
    local_voice_from_musicxml,
    musicxml_voice_for_staff,
)
from evaluation.analysis.music_statistics import parse_pitch_name


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
    "triplet_eighth_basic": 1.0 / 3.0,
}
QUARTERS_TO_DURATION = {
    4.0: "whole",
    3.0: "dotted_half",
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
MUSICXML_ARTICULATIONS = {
    "accent",
    "breath-mark",
    "caesura",
    "detached-legato",
    "doit",
    "falloff",
    "plop",
    "scoop",
    "spiccato",
    "staccatissimo",
    "staccato",
    "stress",
    "strong-accent",
    "tenuto",
    "unstress",
}
MUSICXML_DYNAMICS = {"pppp", "ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "ffff", "fp", "sf", "sfp", "sfpp", "sfz", "sffz", "fz", "rf", "rfz"}


def utc_now() -> str:
    """Return an ISO timestamp for project and operation metadata."""

    return datetime.now(UTC).isoformat()


def new_score_document(
    title: str = "Untitled Sera Score",
    composer: str = "Sera",
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
        "composer": composer,
        "metadata": {
            "created_at": stamp,
            "updated_at": stamp,
            "source": "generated" if prompt else "edited",
            "prompt": prompt,
            "agent_plan_id": "",
            "title": title,
            "composer": composer,
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
        "tracks": [
            {
                "track_id": "piano_right_hand",
                "role": "lead_melody",
                "instrument": "piano",
                "part_id": "piano",
                "staff": "right_hand",
                "voice": 1,
            },
            {
                "track_id": "piano_left_hand",
                "role": "accompaniment",
                "instrument": "piano",
                "part_id": "piano",
                "staff": "left_hand",
                "voice": 1,
            },
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
    _strip_namespaces(root)
    title = root.findtext(".//work-title") or "Imported Sera Score"
    composer = root.findtext(".//creator[@type='composer']") or "Sera"
    key, meter, tempo = _global_from_musicxml(root)
    measure_nodes = root.findall(".//measure")
    measure_count = max(1, len(measure_nodes))
    score = new_score_document(title=title, composer=composer, prompt=prompt, key=key, meter=meter, tempo=tempo, measures=measure_count)
    score["metadata"]["source"] = source
    measure_meta = _measure_labels_from_musicxml(root)
    by_measure = _score_events_from_musicxml(root)
    for measure in score["measures"]:
        number = int(measure["number"])
        labels = measure_meta.get(number, {})
        measure["section"] = labels.get("section", measure["section"])
        measure["harmony"] = labels.get("harmony", measure["harmony"])
        measure["events"] = sorted(
            by_measure.get(number, []),
            key=lambda item: (
                item["staff"],
                Fraction(str(item["offset"])),
                item["voice"],
                bool(item.get("is_chord_tone")),
                item["event_id"],
            ),
        )
    return normalize_score_document(score)


def _strip_namespaces(root: ET.Element) -> None:
    """Normalize namespaced external MusicXML to the repository's local tag form."""

    for element in root.iter():
        if "}" in element.tag:
            element.tag = element.tag.rsplit("}", maxsplit=1)[-1]


def _score_events_from_musicxml(root: ET.Element) -> dict[int, list[dict[str, Any]]]:
    """Parse editable events and Sera metadata without losing note-node alignment."""

    result: dict[int, list[dict[str, Any]]] = {}
    divisions = 1
    generated_index = 0
    # Dynamics are persistent notation state.  Keep the state per staff/voice
    # because Sera's exporter emits one note-level mark for each lane and then
    # omits repetitions.  A staff-wide <direction> supplies the fallback for
    # lanes that have not established their own note-level state.
    active_dynamic_by_lane: dict[tuple[str, int], str] = {}
    active_dynamic_by_staff: dict[str, str] = {"right_hand": "mf", "left_hand": "mf"}
    for measure_index, measure in enumerate(root.findall(".//measure"), start=1):
        number = int(measure.get("number") or measure_index)
        attributes = measure.find("attributes")
        if attributes is not None:
            divisions = max(1, _int_text(attributes.find("divisions"), divisions))
        direction_dynamics = _direction_dynamics(measure, divisions)
        measure_dynamic_source_offsets: dict[tuple[str, int], Fraction] = {}
        voice_cursors: dict[tuple[str, int], Fraction] = {}
        events: list[dict[str, Any]] = []
        for note in measure.findall("note"):
            generated_index += 1
            staff_number = note.findtext("staff") or "1"
            staff = "left_hand" if staff_number == "2" else "right_hand"
            voice_text = note.findtext("voice") or "1"
            raw_voice = int(voice_text) if voice_text.isdigit() else 1
            voice = local_voice_from_musicxml(raw_voice)
            lane = (staff, voice)
            grace = note.find("grace") is not None
            duration_ticks = _int_text(note.find("duration"), 0)
            duration = Fraction(duration_ticks, divisions) if duration_ticks else Fraction(0)
            is_chord_tone = note.find("chord") is not None
            offset = voice_cursors.get(lane, Fraction(0))
            if is_chord_tone and duration:
                offset -= duration
            is_rest = note.find("rest") is not None
            pitch_node = note.find("pitch")
            pitch = ""
            if pitch_node is not None and not is_rest:
                step = (pitch_node.findtext("step") or "C").strip().upper()
                alter = _int_text(pitch_node.find("alter"), 0)
                octave = _int_text(pitch_node.find("octave"), 4)
                accidental = "#" * alter if alter > 0 else "b" * abs(alter)
                pitch = f"{step}{accidental}{octave}"
            event_id = _technical_value(note, "sera-event-id:") or f"m{number}_e{generated_index}"
            tie = _relation_value(node.get("type") for node in note.findall("tie"))
            if tie is None:
                tie = _relation_value(node.get("type") for node in note.findall("./notations/tied"))
            slur = _relation_value(node.get("type") for node in note.findall("./notations/slur"))
            dynamic = active_dynamic_by_lane.get(lane, active_dynamic_by_staff.get(staff, "mf"))
            direction_mark = _dynamic_mark_at_offset(direction_dynamics, staff, offset)
            previous_source_offset = measure_dynamic_source_offsets.get(lane, Fraction(-1))
            if direction_mark is not None and direction_mark[0] > previous_source_offset:
                direction_offset, dynamic = direction_mark
                active_dynamic_by_lane[lane] = dynamic
                measure_dynamic_source_offsets[lane] = direction_offset
            note_dynamic = _dynamic_from_note(note)
            if note_dynamic:
                dynamic = note_dynamic
                active_dynamic_by_lane[lane] = dynamic
                # Note-level dynamics occur after directions at the same
                # MusicXML position, so they win ties and persist afterward.
                measure_dynamic_source_offsets[lane] = offset
            articulations = [
                child.tag
                for child in note.findall("./notations/articulations/*")
                if child.tag in MUSICXML_ARTICULATIONS
            ]
            duration_label = (
                "eighth"
                if grace
                else "triplet_eighth"
                if note.find("time-modification") is not None and duration == Fraction(1, 3)
                else _duration_label(float(duration), note.find("dot") is not None)
            )
            beam_node = note.find("beam")
            event: dict[str, Any] = {
                "event_id": event_id,
                "type": "rest" if is_rest else "note",
                "pitch": pitch,
                "duration": duration_label,
                "offset": round(float(offset), 6),
                "voice": voice,
                "staff": staff,
                "tie": tie,
                "slur": slur,
                "accidental": note.findtext("accidental") or "",
                "dynamic": dynamic,
                "articulations": articulations,
                "grace": grace,
                "is_chord_tone": is_chord_tone,
                "chord_group_id": _technical_value(note, "sera-chord-group-id:"),
                "selected": False,
            }
            if beam_node is not None and (beam_node.text or "").strip():
                event["beam"] = {
                    "number": int(beam_node.get("number") or 1),
                    "value": (beam_node.text or "").strip(),
                }
            events.append(event)
            if not is_chord_tone and not grace:
                voice_cursors[lane] = voice_cursors.get(lane, Fraction(0)) + duration
        _assign_chord_groups(events, number)
        result[number] = events
        for staff in ("right_hand", "left_hand"):
            staff_marks = [item for item in direction_dynamics if item[0] == staff]
            if not staff_marks:
                continue
            _, last_offset, last_value = staff_marks[-1]
            active_dynamic_by_staff[staff] = last_value
            for lane in [key for key in active_dynamic_by_lane if key[0] == staff]:
                if last_offset > measure_dynamic_source_offsets.get(lane, Fraction(-1)):
                    active_dynamic_by_lane[lane] = last_value
    return result


def _technical_value(note: ET.Element, prefix: str) -> str | None:
    for node in note.findall("./notations/technical/other-technical"):
        value = (node.text or "").strip()
        if value.startswith(prefix):
            return value[len(prefix) :].strip() or None
    return None


def _relation_value(values: Any) -> str | None:
    kinds = {str(value) for value in values if value in {"start", "stop", "continue"}}
    if "continue" in kinds or {"start", "stop"} <= kinds:
        return "continue"
    if "start" in kinds:
        return "start"
    if "stop" in kinds:
        return "stop"
    return None


def _dynamic_from_note(note: ET.Element) -> str | None:
    dynamics = note.find("./notations/dynamics")
    if dynamics is None:
        return None
    for child in list(dynamics):
        if child.tag in MUSICXML_DYNAMICS:
            return child.tag
        if child.tag == "other-dynamics" and (child.text or "").strip():
            return (child.text or "").strip()
    return None


def _direction_dynamics(measure: ET.Element, divisions: int) -> list[tuple[str, Fraction, str]]:
    """Read standard MusicXML direction dynamics at their measure positions."""

    cursor = Fraction(0)
    marks: list[tuple[str, Fraction, str]] = []
    for child in list(measure):
        if child.tag == "backup":
            cursor = max(Fraction(0), cursor - Fraction(_int_text(child.find("duration"), 0), divisions))
        elif child.tag == "forward":
            cursor += Fraction(_int_text(child.find("duration"), 0), divisions)
        elif child.tag == "note":
            if child.find("chord") is None and child.find("grace") is None:
                cursor += Fraction(_int_text(child.find("duration"), 0), divisions)
        elif child.tag == "direction":
            dynamics = child.find("./direction-type/dynamics")
            if dynamics is None:
                continue
            value = next(
                (
                    node.tag
                    if node.tag in MUSICXML_DYNAMICS
                    else (node.text or "").strip()
                    for node in list(dynamics)
                    if node.tag in MUSICXML_DYNAMICS or node.tag == "other-dynamics"
                ),
                "",
            )
            if not value:
                continue
            staff = "left_hand" if (child.findtext("staff") or "1") == "2" else "right_hand"
            offset = Fraction(_int_text(child.find("offset"), 0), divisions)
            marks.append((staff, max(Fraction(0), cursor + offset), value))
    return sorted(marks, key=lambda item: (item[0], item[1]))


def _dynamic_at_offset(
    marks: list[tuple[str, Fraction, str]],
    staff: str,
    offset: Fraction,
    fallback: str,
) -> str:
    mark = _dynamic_mark_at_offset(marks, staff, offset)
    return mark[1] if mark is not None else fallback


def _dynamic_mark_at_offset(
    marks: list[tuple[str, Fraction, str]],
    staff: str,
    offset: Fraction,
) -> tuple[Fraction, str] | None:
    """Return the last staff-wide dynamic mark active at an offset."""

    result: tuple[Fraction, str] | None = None
    for mark_staff, mark_offset, mark_value in marks:
        if mark_staff == staff and mark_offset <= offset:
            result = (mark_offset, mark_value)
    return result


def _assign_chord_groups(events: list[dict[str, Any]], measure_number: int) -> None:
    groups: dict[tuple[str, int, Fraction], list[dict[str, Any]]] = {}
    for event in events:
        if event.get("type") == "rest" or event.get("grace"):
            continue
        key = (
            str(event.get("staff", "right_hand")),
            int(event.get("voice", 1) or 1),
            Fraction(str(event.get("offset", 0))),
        )
        groups.setdefault(key, []).append(event)
    for (staff, voice, offset), group in groups.items():
        if len(group) < 2:
            group[0]["chord_group_id"] = group[0].get("chord_group_id") or None
            group[0]["is_chord_tone"] = False
            continue
        explicit = next((str(item["chord_group_id"]) for item in group if item.get("chord_group_id")), None)
        group_id = explicit or f"m{measure_number}:{staff}:v{voice}:o{offset}"
        for index, event in enumerate(group):
            event["chord_group_id"] = group_id
            event["is_chord_tone"] = index > 0


def score_document_to_musicxml(score: dict[str, Any]) -> str:
    """Export a ScoreDocument to parseable MusicXML."""

    score = prepare_score_document_for_export(score)
    _mark_dynamic_changes_for_export(score)
    global_info = score.get("global", {})
    key = str(global_info.get("key", "C major"))
    meter = str(global_info.get("meter", "4/4"))
    tempo = int(global_info.get("tempo", 90))
    beats, beat_type = _parse_meter(meter)
    divisions = 12 if _score_uses_triplets(score) else 4
    expected = int(beats * divisions * (4 / beat_type))
    measures = score.get("measures") or []
    measure_xml = [
        _measure_to_xml(
            measure,
            key,
            beats,
            beat_type,
            divisions,
            expected,
            first=index == 0,
            tempo=tempo,
        )
        for index, measure in enumerate(measures)
    ]
    title = escape(str(score.get("title") or "Untitled Sera Score"))
    composer = escape(str(score.get("composer") or "Sera"))
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
            '<score-partwise version="3.1">',
            "  <work>",
            f"    <work-title>{title}</work-title>",
            "  </work>",
            "  <identification>",
            f"    <creator type=\"composer\">{composer}</creator>",
            "  </identification>",
            "  <part-list>",
            "    <score-part id=\"P1\"><part-name>Piano</part-name></score-part>",
            "  </part-list>",
            "  <part id=\"P1\">",
            *measure_xml,
            "  </part>",
            "</score-partwise>",
            "",
        ]
    )


def score_document_to_note_events(score: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a ScoreDocument into MIDI exporter note events."""

    score = normalize_score_document(score)
    score = _notation_normalized(score)
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
    normalized["title"] = str(normalized.get("title") or "Untitled Sera Score")
    normalized["composer"] = str(normalized.get("composer") or "Sera")
    normalized["metadata"].setdefault("created_at", utc_now())
    normalized["metadata"]["updated_at"] = utc_now()
    normalized["metadata"].setdefault("source", "edited")
    normalized["metadata"].setdefault("prompt", "")
    normalized["metadata"].setdefault("agent_plan_id", "")
    normalized["metadata"]["title"] = normalized["title"]
    normalized["metadata"]["composer"] = normalized["composer"]
    normalized["global"].setdefault("key", "C major")
    normalized["global"].setdefault("meter", "4/4")
    normalized["global"].setdefault("tempo", 90)
    normalized["global"].setdefault("pickup", False)
    normalized.setdefault("parts", template["parts"])
    normalized["tracks"] = _normalize_tracks(normalized.get("tracks"), normalized)
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
            event.setdefault("grace", False)
            event.setdefault("is_chord_tone", False)
            event.setdefault("chord_group_id", None)
            event.setdefault("selected", False)
    normalized["measures"] = measures
    return normalized


def infer_score_tracks(score: dict[str, Any]) -> list[dict[str, Any]]:
    """Infer minimal track roles from piano staff/voice usage."""

    events = [event for measure in score.get("measures", []) for event in measure.get("events", [])]
    tracks: list[dict[str, Any]] = []
    right_voices = sorted({int(event.get("voice", 1) or 1) for event in events if event.get("staff", "right_hand") != "left_hand"}) or [1]
    left_voices = sorted({int(event.get("voice", 1) or 1) for event in events if event.get("staff") == "left_hand"})
    for voice in right_voices:
        tracks.append(
            {
                "track_id": f"piano_right_hand_v{voice}",
                "role": "lead_melody" if voice == 1 else "inner_voice",
                "instrument": "piano",
                "part_id": "piano",
                "staff": "right_hand",
                "voice": voice,
            }
        )
    for voice in left_voices or [1]:
        tracks.append(
            {
                "track_id": f"piano_left_hand_v{voice}",
                "role": "bass" if voice == 1 else "rhythmic_pattern",
                "instrument": "piano",
                "part_id": "piano",
                "staff": "left_hand",
                "voice": voice,
            }
        )
    return tracks


def build_role_coverage_report(score: dict[str, Any]) -> dict[str, bool]:
    """Summarize whether the score covers the main future orchestration roles."""

    events = [event for measure in score.get("measures", []) for event in measure.get("events", []) if event.get("type") != "rest"]
    right = [event for event in events if event.get("staff", "right_hand") != "left_hand"]
    left = [event for event in events if event.get("staff") == "left_hand"]
    chordal = [event for event in events if event.get("type") == "chord" or event.get("pitches")]
    varied_durations = len({str(event.get("duration", "")) for event in events}) >= 2
    return {
        "lead_melody": bool(right),
        "harmony": bool(chordal or left),
        "bass": bool(left),
        "rhythm": bool(varied_durations),
        "accompaniment": bool(left),
    }


def _normalize_tracks(tracks: Any, score: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(tracks, list) or not tracks:
        return infer_score_tracks(score)
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(tracks, start=1):
        if not isinstance(item, dict):
            continue
        track = {
            "track_id": str(item.get("track_id") or f"track_{index}"),
            "role": str(item.get("role") or "lead_melody"),
            "instrument": str(item.get("instrument") or "piano"),
            "part_id": str(item.get("part_id") or "piano"),
            "staff": str(item.get("staff") or "right_hand"),
            "voice": int(item.get("voice", 1) or 1),
        }
        normalized.append(track)
    return normalized or infer_score_tracks(score)


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
    tempo: int,
) -> str:
    right = [event for event in measure.get("events", []) if event.get("staff", "right_hand") != "left_hand"]
    left = [event for event in measure.get("events", []) if event.get("staff") == "left_hand"]
    lines = [f'      <measure number="{int(measure.get("number", 1))}">']
    if first:
        lines.extend(_attributes_xml(key, beats, beat_type, divisions))
        lines.append(
            f"        <direction placement=\"above\"><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>{tempo}</per-minute></metronome></direction-type></direction>"
        )
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


def prepare_score_document_for_export(score: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical notation state used by MusicXML export."""

    prepared = normalize_score_document(score)
    prepared = _notation_normalized(prepared)
    return materialize_beams_for_score_document(prepared)


def _mark_dynamic_changes_for_export(score: dict[str, Any]) -> None:
    """Emit persistent dynamics once per staff/voice until their value changes.

    ScoreDocument stores the effective dynamic on every event so playback does
    not need to reconstruct dynamic state. Writing that denormalized value on
    every MusicXML note produces an unusable row of repeated ``mf`` marks in
    notation hosts. This private export marker keeps round-trip semantics while
    serializing only the first mark and subsequent changes.
    """

    active: dict[tuple[str, int], str] = {}
    for measure in score.get("measures") or []:
        groups: dict[tuple[str, int, Fraction], list[dict[str, Any]]] = {}
        for event in measure.get("events") or []:
            event["_emit_dynamic"] = False
            if event.get("type") == "rest" or event.get("grace"):
                continue
            key = (
                str(event.get("staff", "right_hand")),
                int(event.get("voice", 1) or 1),
                Fraction(str(event.get("offset", 0))),
            )
            groups.setdefault(key, []).append(event)
        for (staff, voice, _offset), group in sorted(groups.items(), key=lambda item: item[0]):
            primary = next((event for event in group if not event.get("is_chord_tone")), group[0])
            dynamic = str(primary.get("dynamic") or "").strip().lower()
            state_key = (staff, voice)
            if dynamic and dynamic != active.get(state_key):
                primary["_emit_dynamic"] = True
                active[state_key] = dynamic


def _staff_events_to_xml(events: list[dict[str, Any]], expected: int, divisions: int, staff_number: int) -> list[str]:
    lines: list[str] = []
    by_voice: dict[int, list[dict[str, Any]]] = {}
    for event in events:
        by_voice.setdefault(int(event.get("voice", 1) or 1), []).append(event)
    previous_voice_end = 0
    for voice_index, (voice, voice_events) in enumerate(sorted(by_voice.items()) or [(1, [])]):
        if voice_index:
            lines.extend(["        <backup>", f"          <duration>{previous_voice_end}</duration>", "        </backup>"])
        cursor = 0
        event_groups: dict[int, list[dict[str, Any]]] = {}
        for event in voice_events:
            offset = max(0, int(round(float(event.get("offset", 0.0)) * divisions)))
            event_groups.setdefault(offset, []).append(event)
        for offset, group in sorted(event_groups.items()):
            if offset > cursor:
                lines.extend(_rest_xml(offset - cursor, staff_number, voice=voice, divisions=divisions))
                cursor = offset
            ordered = sorted(
                group,
                key=lambda item: (
                    not bool(item.get("grace")),
                    bool(item.get("is_chord_tone")),
                    str(item.get("event_id", "")),
                ),
            )
            grace_notes = [event for event in ordered if event.get("grace") and event.get("type") != "rest"]
            for event in grace_notes:
                lines.extend(
                    _note_xml(
                        str(event.get("pitch", "C4")),
                        0,
                        divisions,
                        staff_number,
                        voice,
                        event,
                        grace=True,
                    )
                )
            sounding = [event for event in ordered if not event.get("grace")]
            rests = [event for event in sounding if event.get("type") == "rest"]
            notes = [event for event in sounding if event.get("type") != "rest"]
            if rests and not notes:
                duration = _event_duration_ticks(rests[0], divisions)
                lines.extend(_rest_xml(duration, staff_number, rests[0], voice=voice, divisions=divisions))
                cursor += duration
            elif notes:
                primary = next((event for event in notes if not event.get("is_chord_tone")), notes[0])
                ordered_notes = [primary, *(event for event in notes if event is not primary)]
                for index, event in enumerate(ordered_notes):
                    lines.extend(
                        _note_xml(
                            str(event.get("pitch", "C4")),
                            _event_duration_ticks(event, divisions),
                            divisions,
                            staff_number,
                            voice,
                            event,
                            chord=index > 0,
                        )
                    )
                cursor += _event_duration_ticks(primary, divisions)
        if cursor < expected:
            lines.extend(_rest_xml(expected - cursor, staff_number, voice=voice, divisions=divisions))
            cursor = expected
        previous_voice_end = cursor
    return lines


def _note_xml(
    pitch: str,
    duration: int,
    divisions: int,
    staff_number: int,
    voice: int,
    event: dict[str, Any] | None = None,
    chord: bool = False,
    grace: bool = False,
) -> list[str]:
    step, alter, octave = _pitch_components(pitch)
    note_type, dotted, triplet = _duration_type(duration, divisions)
    lines = [
        f"        <!-- sera-event-id:{escape(str((event or {}).get('event_id', '')))} -->",
        "        <note>",
    ]
    if grace:
        lines.append("          <grace slash=\"yes\"/>")
    if chord:
        lines.append("          <chord/>")
    lines.extend(["          <pitch>", f"            <step>{step}</step>"])
    if alter:
        lines.append(f"            <alter>{alter}</alter>")
    lines.extend(
        [
            f"            <octave>{octave}</octave>",
            "          </pitch>",
        ]
    )
    if not grace:
        lines.append(f"          <duration>{duration}</duration>")
    for tie_type in _musicxml_relation_types((event or {}).get("tie")):
        lines.append(f"          <tie type=\"{tie_type}\"/>")
    musicxml_voice = musicxml_voice_for_staff(voice, staff_number)
    lines.extend([f"          <voice>{musicxml_voice}</voice>", f"          <type>{note_type}</type>"])
    if dotted:
        lines.append("          <dot/>")
    accidental = _accidental_xml_value((event or {}).get("accidental"))
    if accidental:
        lines.append(f"          <accidental>{accidental}</accidental>")
    if triplet:
        lines.extend(
            [
                "          <time-modification>",
                "            <actual-notes>3</actual-notes>",
                "            <normal-notes>2</normal-notes>",
                "            <normal-type>eighth</normal-type>",
                "          </time-modification>",
            ]
        )
    lines.append(f"          <staff>{staff_number}</staff>")
    beam = (event or {}).get("beam")
    if beam:
        lines.append(f"          <beam number=\"{int(beam.get('number', 1))}\">{escape(str(beam.get('value', 'continue')))}</beam>")
    lines.extend(_notations_xml(event))
    lines.append("        </note>")
    return lines


def _rest_xml(
    duration: int,
    staff_number: int,
    event: dict[str, Any] | None = None,
    *,
    voice: int = 1,
    divisions: int = 4,
) -> list[str]:
    note_type, dotted, triplet = _duration_type(duration, divisions)
    lines = [
        f"        <!-- sera-event-id:{escape(str((event or {}).get('event_id', 'auto-rest')))} -->",
        "        <note>",
        "          <rest/>",
        f"          <duration>{duration}</duration>",
        f"          <voice>{musicxml_voice_for_staff(voice, staff_number)}</voice>",
        f"          <type>{note_type}</type>",
    ]
    if dotted:
        lines.append("          <dot/>")
    if triplet:
        lines.extend(
            [
                "          <time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes><normal-type>eighth</normal-type></time-modification>"
            ]
        )
    lines.append(f"          <staff>{staff_number}</staff>")
    lines.extend(_notations_xml(event))
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


def _score_uses_triplets(score: dict[str, Any]) -> bool:
    return any(
        str(event.get("duration", "")).replace("-", "_").startswith("triplet_")
        for measure in score.get("measures") or []
        for event in measure.get("events") or []
    )


def _event_duration_ticks(event: dict[str, Any], divisions: int) -> int:
    duration = Fraction(str(duration_to_quarters(str(event.get("duration", "quarter")))))
    return max(1, int(round(float(duration * divisions))))


def _duration_type(duration: int, divisions: int = 4) -> tuple[str, bool, bool]:
    value = Fraction(duration, max(1, divisions))
    mapping = {
        Fraction(1, 4): ("16th", False, False),
        Fraction(1, 3): ("eighth", False, True),
        Fraction(1, 2): ("eighth", False, False),
        Fraction(3, 4): ("eighth", True, False),
        Fraction(1, 1): ("quarter", False, False),
        Fraction(3, 2): ("quarter", True, False),
        Fraction(2, 1): ("half", False, False),
        Fraction(3, 1): ("half", True, False),
        Fraction(4, 1): ("whole", False, False),
    }
    return mapping.get(value, ("quarter", False, False))


def _pitch_components(pitch: str) -> tuple[str, int, int]:
    match = re.fullmatch(r"([A-Ga-g])([#b]*)(-?\d+)", str(pitch).strip())
    if match:
        accidental = match.group(2)
        alter = accidental.count("#") - accidental.count("b")
        return match.group(1).upper(), alter, int(match.group(3))
    midi = parse_pitch_name(pitch) or 60
    step, alter = SEMITONE_TO_STEP[midi % 12]
    return step, alter, midi // 12 - 1


def _musicxml_relation_types(value: object) -> list[str]:
    if value == "continue":
        return ["stop", "start"]
    if value in {"start", "stop"}:
        return [str(value)]
    return []


def _accidental_xml_value(value: object) -> str:
    aliases = {
        "#": "sharp",
        "sharp": "sharp",
        "b": "flat",
        "flat": "flat",
        "natural": "natural",
        "##": "double-sharp",
        "double_sharp": "double-sharp",
        "double-sharp": "double-sharp",
        "bb": "flat-flat",
        "double_flat": "flat-flat",
        "double-flat": "flat-flat",
        "flat-flat": "flat-flat",
    }
    return aliases.get(str(value or "").strip().lower(), "")


def _notations_xml(event: dict[str, Any] | None) -> list[str]:
    if event is None:
        return []
    contents: list[str] = []
    for tie_type in _musicxml_relation_types(event.get("tie")):
        contents.append(f"            <tied type=\"{tie_type}\"/>")
    slur = event.get("slur")
    if slur in {"start", "stop", "continue"}:
        contents.append(f"            <slur type=\"{slur}\" number=\"1\"/>")
    articulations = [
        str(value).strip().lower().replace("_", "-")
        for value in event.get("articulations") or []
        if str(value).strip().lower().replace("_", "-") in MUSICXML_ARTICULATIONS
    ]
    if articulations:
        contents.append("            <articulations>")
        contents.extend(f"              <{name}/>" for name in articulations)
        contents.append("            </articulations>")
    dynamic = str(event.get("dynamic") or "").strip().lower() if event.get("_emit_dynamic", True) else ""
    if dynamic:
        contents.append("            <dynamics>")
        if dynamic in MUSICXML_DYNAMICS:
            contents.append(f"              <{dynamic}/>")
        else:
            contents.append(f"              <other-dynamics>{escape(dynamic)}</other-dynamics>")
        contents.append("            </dynamics>")
    contents.extend(
        [
            "            <technical>",
            f"              <other-technical>sera-event-id:{escape(str(event.get('event_id', '')))}</other-technical>",
        ]
    )
    if event.get("chord_group_id"):
        contents.append(
            f"              <other-technical>sera-chord-group-id:{escape(str(event['chord_group_id']))}</other-technical>"
        )
    contents.append("            </technical>")
    return ["          <notations>", *contents, "          </notations>"]


def _duration_label(duration_quarter: float, dotted: bool = False) -> str:
    if dotted:
        dotted_labels = {
            0.75: "dotted_eighth",
            1.5: "dotted_quarter",
            3.0: "dotted_half",
        }
        for quarters, label in dotted_labels.items():
            if abs(duration_quarter - quarters) < 0.02:
                return label
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


def _notation_normalized(score: dict[str, Any]) -> dict[str, Any]:
    """Run V0.93 notation normalization without making old imports fragile."""

    if score.get("metadata", {}).get("notation_normalized"):
        return score
    try:
        from backend.notation.notation_normalizer import normalize_score_document as normalize_notation_score_document

        return normalize_notation_score_document(score).score_document
    except Exception:  # noqa: BLE001 - export must remain fallback-safe.
        return score

"""Convert Sera V0.5 structured events back to legal MusicXML."""

from __future__ import annotations

from html import escape
from typing import Iterable

from evaluation.analysis.music_statistics import parse_pitch_name
from training.tokenization.structured_events import TOKEN_TO_DURATION, decode_note_token


def structured_events_to_musicxml(events: Iterable[str], title: str = "Sera V0.5 Structured Events") -> str:
    """Create a simple monophonic MusicXML score from structured events."""

    event_list = list(events)
    key = _first_value(event_list, "KEY_", "C_MAJOR").replace("_", " ").title()
    meter = _first_value(event_list, "METER_", "4_4").replace("_", "/")
    beats, beat_type = _parse_meter(meter)
    expected = int(beats * 4 * (4 / beat_type))
    measures = _event_measures(event_list)
    if not measures:
        measures = [[("NOTE_C4", "RHYTHM_QUARTER")]]
    measure_xml = []
    for index, items in enumerate(measures, start=1):
        measure_xml.append(_measure_xml(index, items, key, beats, beat_type, expected, first=index == 1))
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<score-partwise version="3.1">',
            "  <work>",
            f"    <work-title>{escape(title)}</work-title>",
            "  </work>",
            "  <part-list>",
            '    <score-part id="P1"><part-name>Piano</part-name></score-part>',
            "  </part-list>",
            '  <part id="P1">',
            *measure_xml,
            "  </part>",
            "</score-partwise>",
            "",
        ]
    )


def _event_measures(events: list[str]) -> list[list[tuple[str, str]]]:
    measures: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    pending_rhythm = "RHYTHM_QUARTER"
    for token in events:
        if token == "BAR":
            if current:
                measures.append(current)
            current = []
            pending_rhythm = "RHYTHM_QUARTER"
        elif token.startswith("RHYTHM_"):
            pending_rhythm = token
            if token.startswith("RHYTHM_REST"):
                current.append(("REST", token))
        elif token.startswith("NOTE_") or token.startswith("CHORD_"):
            current.append((token, pending_rhythm))
    if current:
        measures.append(current)
    return measures


def _measure_xml(
    index: int,
    items: list[tuple[str, str]],
    key: str,
    beats: int,
    beat_type: int,
    expected: int,
    first: bool,
) -> str:
    lines = [f'      <measure number="{index}">']
    if first:
        lines.extend(
            [
                "        <attributes>",
                "          <divisions>4</divisions>",
                "          <key>",
                f"            <fifths>{_key_fifths(key)}</fifths>",
                f"            <mode>{'minor' if 'minor' in key.lower() else 'major'}</mode>",
                "          </key>",
                "          <time>",
                f"            <beats>{beats}</beats>",
                f"            <beat-type>{beat_type}</beat-type>",
                "          </time>",
                "          <clef><sign>G</sign><line>2</line></clef>",
                "        </attributes>",
            ]
        )
    used = 0
    for token, rhythm in items:
        duration = int(TOKEN_TO_DURATION.get(rhythm, 1.0) * 4)
        if used + duration > expected:
            duration = max(1, expected - used)
        if duration <= 0:
            continue
        if token == "REST" or rhythm.startswith("RHYTHM_REST"):
            lines.extend(_rest_xml(duration))
        elif token.startswith("CHORD_"):
            pitches = [decode_note_token(part) or "C4" for part in token.removeprefix("CHORD_").split("_")]
            for chord_index, pitch in enumerate(pitches):
                lines.extend(_note_xml(pitch, duration, chord=chord_index > 0))
        else:
            lines.extend(_note_xml(decode_note_token(token) or "C4", duration))
        used += duration
    if used < expected:
        lines.extend(_rest_xml(expected - used))
    lines.append("      </measure>")
    return "\n".join(lines)


def _note_xml(pitch_name: str, duration: int, chord: bool = False) -> list[str]:
    midi = parse_pitch_name(pitch_name) or 60
    step = pitch_name[0].upper() if pitch_name else "C"
    alter = 1 if "#" in pitch_name else -1 if "b" in pitch_name else 0
    octave = midi // 12 - 1
    note_type, dotted = _duration_type(duration)
    lines = ["        <note>"]
    if chord:
        lines.append("          <chord/>")
    lines.extend(["          <pitch>", f"            <step>{step}</step>"])
    if alter:
        lines.append(f"            <alter>{alter}</alter>")
    lines.extend(
        [
            f"            <octave>{octave}</octave>",
            "          </pitch>",
            f"          <duration>{duration}</duration>",
            "          <voice>1</voice>",
            f"          <type>{note_type}</type>",
        ]
    )
    if dotted:
        lines.append("          <dot/>")
    lines.append("        </note>")
    return lines


def _rest_xml(duration: int) -> list[str]:
    note_type, dotted = _duration_type(duration)
    lines = [
        "        <note>",
        "          <rest/>",
        f"          <duration>{duration}</duration>",
        "          <voice>1</voice>",
        f"          <type>{note_type}</type>",
    ]
    if dotted:
        lines.append("          <dot/>")
    lines.append("        </note>")
    return lines


def _duration_type(duration: int) -> tuple[str, bool]:
    mapping = {1: ("16th", False), 2: ("eighth", False), 4: ("quarter", False), 6: ("quarter", True), 8: ("half", False), 16: ("whole", False)}
    return mapping.get(duration, ("quarter", False))


def _parse_meter(meter: str) -> tuple[int, int]:
    try:
        beats, beat_type = meter.split("/")
        return int(beats), int(beat_type)
    except ValueError:
        return 4, 4


def _first_value(events: list[str], prefix: str, fallback: str) -> str:
    for event in events:
        if event.startswith(prefix):
            return event.removeprefix(prefix)
    return fallback


def _key_fifths(key: str) -> int:
    tonic = key.split()[0].replace("-Flat", "b").replace("-flat", "b")
    return {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "F#": 6, "F": -1, "Bb": -2}.get(tonic, 0)

"""Rule-based symbolic generator for Sera V0.2.

The generator favors legal, parseable MusicXML over complex notation.  It can
emit a piano single-line sketch or a simplified two-staff piano texture using
deterministic motifs, phrase repetition, basic harmony, and cadences.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

from backend.models.schemas import CompositionPlan, MeasurePlan


STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MAJOR_DEGREES = {"1": 0, "2": 2, "3": 4, "4": 5, "5": 7, "6": 9, "7": 11}
MINOR_DEGREES = {"1": 0, "2": 2, "b3": 3, "3": 3, "4": 5, "5": 7, "b6": 8, "6": 8, "7": 11}
SEMITONE_TO_PITCH = {
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


@dataclass(slots=True)
class GeneratedScore:
    """In-memory symbolic score payloads."""

    musicxml: str
    abc: str
    note_events: list[dict[str, Any]]


class RuleBasedGenerator:
    """Generate legal 8, 16, or 32 measure MusicXML from a composition plan."""

    def generate(self, plan: CompositionPlan) -> GeneratedScore:
        """Return MusicXML, ABC, and note events for the supplied plan."""

        intent = plan.intent
        time = self._time_info(intent.time_signature)
        tonic = self._tonic(intent.key)
        tonic_pc = self._tonic_pc(tonic)
        mode = "minor" if "minor" in intent.key.lower() else "major"
        two_staff = self._use_two_staff(intent.instruments, intent.texture)

        measure_xml: list[str] = []
        abc_measures: list[str] = []
        note_events: list[dict[str, Any]] = []
        cursor_quarters = 0.0

        for measure in plan.measures:
            right_events = self._right_hand_events(measure, intent.texture, tonic_pc, mode, time)
            left_events = (
                self._left_hand_events(measure, intent.texture, tonic_pc, mode, time)
                if two_staff
                else []
            )
            measure_xml.append(
                self._measure_xml(
                    measure=measure,
                    right_events=right_events,
                    left_events=left_events,
                    key=intent.key,
                    time=time,
                    first_measure=measure.index == 1,
                    two_staff=two_staff,
                )
            )
            note_events.extend(
                self._events_to_midi_payload(right_events + left_events, measure.index, cursor_quarters, time)
            )
            abc_measures.append(" ".join(self._abc_note(self._pitch_name(event["pitches"][0])) for event in right_events))
            cursor_quarters += time["quarter_total"]

        title = escape(intent.title or f"Sera draft - {intent.style}")
        part_name = "Piano" if two_staff else escape(intent.instruments[0])
        musicxml = "\n".join(
            [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
                '<score-partwise version="3.1">',
                "  <work>",
                f"    <work-title>{title}</work-title>",
                "  </work>",
                "  <identification>",
                "    <creator type=\"composer\">Sera rule-based generator V0.2</creator>",
                "  </identification>",
                "  <part-list>",
                "    <score-part id=\"P1\">",
                f"      <part-name>{part_name}</part-name>",
                "    </score-part>",
                "  </part-list>",
                "  <part id=\"P1\">",
                *measure_xml,
                "  </part>",
                "</score-partwise>",
                "",
            ]
        )
        abc = "\n".join(
            [
                "X:1",
                f"T:{intent.title}",
                f"M:{intent.time_signature}",
                "L:1/8",
                f"Q:1/4={intent.tempo_bpm}",
                f"K:{self._abc_key(intent.key)}",
                "| " + " | ".join(abc_measures) + " |",
                "",
            ]
        )
        return GeneratedScore(musicxml=musicxml, abc=abc, note_events=note_events)

    @staticmethod
    def _use_two_staff(instruments: list[str], texture: str) -> bool:
        if texture == "single_line":
            return False
        return any("piano" in instrument.lower() for instrument in instruments)

    @staticmethod
    def _time_info(signature: str) -> dict[str, Any]:
        beats, beat_type = [int(part) for part in signature.split("/")]
        divisions = 2
        expected = int(beats * divisions * (4 / beat_type))
        return {
            "beats": beats,
            "beat_type": beat_type,
            "divisions": divisions,
            "expected_duration": expected,
            "quarter_total": beats * (4 / beat_type),
        }

    def _right_hand_events(
        self,
        measure: MeasurePlan,
        texture: str,
        tonic_pc: int,
        mode: str,
        time: dict[str, Any],
    ) -> list[dict[str, Any]]:
        durations = self._melody_durations(time, measure.cadence, texture)
        count = len(durations)
        melody = self._melody_pitches(measure.notes, tonic_pc, mode, count, measure.cadence)
        if texture == "chordal":
            chord = self._chord_pitches(measure.chord, tonic_pc, mode, octave=4, low=57, high=84)
            return [
                self._event(chord, duration, 1, 1, offset)
                for offset, duration in self._offsets(durations)
            ]
        return [
            self._event([pitch], duration, 1, 1, offset)
            for pitch, (offset, duration) in zip(melody, self._offsets(durations), strict=False)
        ]

    def _left_hand_events(
        self,
        measure: MeasurePlan,
        texture: str,
        tonic_pc: int,
        mode: str,
        time: dict[str, Any],
    ) -> list[dict[str, Any]]:
        chord = self._chord_pitches(measure.chord, tonic_pc, mode, octave=3, low=36, high=60)
        bass = self._bass_pitch(chord[0])
        total = time["expected_duration"]
        if texture == "arpeggiated":
            pattern = [bass, chord[1], chord[2], chord[1]]
            durations = [1] * total
            pitches = [pattern[index % len(pattern)] for index in range(len(durations))]
            return [self._event([pitch], duration, 2, 2, offset) for pitch, (offset, duration) in zip(pitches, self._offsets(durations), strict=False)]
        if texture == "simple_counterpoint":
            durations = self._melody_durations(time, measure.cadence, texture)
            contour = [chord[2], chord[1], chord[0], bass]
            pitches = [self._bass_pitch(contour[index % len(contour)]) for index in range(len(durations))]
            return [self._event([pitch], duration, 2, 2, offset) for pitch, (offset, duration) in zip(pitches, self._offsets(durations), strict=False)]
        if texture == "chordal":
            durations = [total // 2, total - (total // 2)]
            compact = [self._bass_pitch(note) for note in chord[:3]]
            return [self._event(compact, duration, 2, 2, offset) for offset, duration in self._offsets(durations)]
        durations = [total // 2, total - (total // 2)]
        pitches = [bass, self._bass_pitch(chord[1])]
        return [self._event([pitch], duration, 2, 2, offset) for pitch, (offset, duration) in zip(pitches, self._offsets(durations), strict=False)]

    @staticmethod
    def _event(pitches: list[int], duration: int, voice: int, staff: int, offset: int) -> dict[str, Any]:
        return {"pitches": pitches, "duration": duration, "voice": voice, "staff": staff, "offset": offset}

    @staticmethod
    def _offsets(durations: list[int]) -> list[tuple[int, int]]:
        offset = 0
        pairs = []
        for duration in durations:
            pairs.append((offset, duration))
            offset += duration
        return pairs

    @staticmethod
    def _melody_durations(time: dict[str, Any], cadence: str, texture: str) -> list[int]:
        total = time["expected_duration"]
        if cadence:
            return [total // 2, total - (total // 2)]
        if time["beat_type"] == 8:
            return [1] * total if texture in {"arpeggiated", "simple_counterpoint"} else [3, 3]
        if time["beats"] == 3:
            return [2, 2, 2]
        if texture == "arpeggiated":
            return [2, 2, 2, 2]
        return [2, 2, 2, 2]

    @staticmethod
    def _melody_pitches(
        degree_hints: list[str],
        tonic_pc: int,
        mode: str,
        count: int,
        cadence: str,
    ) -> list[int]:
        if cadence == "authentic cadence":
            degree_hints = ["5", "1"]
        hints = list(degree_hints or ["1", "2", "3", "5"])
        while len(hints) < count:
            hints.extend(hints)
        hints = hints[:count]
        degree_map = MINOR_DEGREES if mode == "minor" else MAJOR_DEGREES
        pitches: list[int] = []
        for pos, degree in enumerate(hints):
            semitone = degree_map.get(degree, 0)
            midi_number = 60 + tonic_pc + semitone
            if pos >= count - 2 and cadence:
                midi_number = 60 + tonic_pc + (7 if degree == "5" else 0)
            while midi_number > 81:
                midi_number -= 12
            while midi_number < 55:
                midi_number += 12
            pitches.append(midi_number)
        return pitches

    @staticmethod
    def _chord_pitches(chord: str, tonic_pc: int, mode: str, octave: int, low: int, high: int) -> list[int]:
        clean = chord.replace("maj7", "").replace("7", "").replace("°", "")
        major = {
            "I": [0, 4, 7],
            "ii": [2, 5, 9],
            "iii": [4, 7, 11],
            "IV": [5, 9, 12],
            "V": [7, 11, 14],
            "vi": [9, 12, 16],
            "VI": [9, 12, 16],
        }
        minor = {
            "i": [0, 3, 7],
            "ii": [2, 5, 8],
            "III": [3, 7, 10],
            "iv": [5, 8, 12],
            "V": [7, 11, 14],
            "v": [7, 10, 14],
            "VI": [8, 12, 15],
            "VII": [10, 14, 17],
        }
        degrees = (minor if mode == "minor" else major).get(clean, [0, 4, 7])
        base = 12 * (octave + 1) + tonic_pc
        pitches = [base + degree for degree in degrees]
        normalized: list[int] = []
        for pitch in pitches:
            while pitch > high:
                pitch -= 12
            while pitch < low:
                pitch += 12
            normalized.append(pitch)
        return sorted(normalized)

    @staticmethod
    def _bass_pitch(pitch: int) -> int:
        while pitch > 52:
            pitch -= 12
        while pitch < 36:
            pitch += 12
        return pitch

    def _measure_xml(
        self,
        measure: MeasurePlan,
        right_events: list[dict[str, Any]],
        left_events: list[dict[str, Any]],
        key: str,
        time: dict[str, Any],
        first_measure: bool,
        two_staff: bool,
    ) -> str:
        attributes = self._attributes_xml(key, time, two_staff) if first_measure else ""
        direction = (
            f"        <direction placement=\"above\"><direction-type><words>"
            f"{escape(measure.section)} {escape(measure.chord)}"
            f"</words></direction-type></direction>"
        )
        parts = [f'      <measure number="{measure.index}">', attributes, direction]
        for event in right_events:
            parts.extend(self._note_group_xml(event))
        if left_events:
            parts.append("        <backup>")
            parts.append(f"          <duration>{time['expected_duration']}</duration>")
            parts.append("        </backup>")
            for event in left_events:
                parts.extend(self._note_group_xml(event))
        parts.append("      </measure>")
        return "\n".join(part for part in parts if part)

    def _note_group_xml(self, event: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        for index, midi_number in enumerate(event["pitches"]):
            lines.extend(
                self._note_xml(
                    note_name=self._pitch_name(midi_number),
                    duration=int(event["duration"]),
                    voice=int(event["voice"]),
                    staff=int(event["staff"]),
                    chord=index > 0,
                )
            )
        return lines

    def _events_to_midi_payload(
        self,
        events: list[dict[str, Any]],
        measure_index: int,
        cursor_quarters: float,
        time: dict[str, Any],
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for event in events:
            start = cursor_quarters + (int(event["offset"]) / time["divisions"])
            duration = int(event["duration"]) / time["divisions"]
            for midi_number in event["pitches"]:
                payload.append(
                    {
                        "measure": measure_index,
                        "pitch": self._pitch_name(midi_number),
                        "midi": midi_number,
                        "start_quarter": start,
                        "duration_quarter": duration,
                        "velocity": 70 if event["staff"] == 1 else 58,
                        "voice": event["voice"],
                        "staff": event["staff"],
                    }
                )
        return payload

    @staticmethod
    def _tonic(key: str) -> str:
        token = key.split()[0].replace("-flat", "b")
        if token not in STEP_TO_SEMITONE and token not in {"C#", "F#", "Bb", "Eb", "Ab", "Db"}:
            return "C"
        return token

    @staticmethod
    def _tonic_pc(tonic: str) -> int:
        if len(tonic) == 1:
            return STEP_TO_SEMITONE.get(tonic, 0)
        step = tonic[0]
        accidental = tonic[1:]
        alter = 1 if accidental == "#" else -1 if accidental == "b" else 0
        return (STEP_TO_SEMITONE.get(step, 0) + alter) % 12

    @staticmethod
    def _pitch_name(midi_number: int) -> str:
        octave = midi_number // 12 - 1
        step, alter = SEMITONE_TO_PITCH[midi_number % 12]
        accidental = "#" if alter == 1 else "b" if alter == -1 else ""
        return f"{step}{accidental}{octave}"

    @staticmethod
    def _parse_pitch_name(note_name: str) -> tuple[str, int, int]:
        step = note_name[0]
        alter = 0
        rest = note_name[1:]
        if rest.startswith("#"):
            alter = 1
            rest = rest[1:]
        elif rest.startswith("b"):
            alter = -1
            rest = rest[1:]
        return step, alter, int(rest)

    @staticmethod
    def _duration_type(duration: int) -> tuple[str, int]:
        mapping = {
            1: ("eighth", 0),
            2: ("quarter", 0),
            3: ("quarter", 1),
            4: ("half", 0),
            6: ("half", 1),
            8: ("whole", 0),
        }
        return mapping.get(duration, ("quarter", 0))

    @classmethod
    def _note_xml(cls, note_name: str, duration: int, voice: int, staff: int, chord: bool = False) -> list[str]:
        step, alter, octave = cls._parse_pitch_name(note_name)
        note_type, dots = cls._duration_type(duration)
        alter_xml = [f"          <alter>{alter}</alter>"] if alter else []
        accidental_xml = []
        if alter == 1:
            accidental_xml = ["        <accidental>sharp</accidental>"]
        elif alter == -1:
            accidental_xml = ["        <accidental>flat</accidental>"]
        lines = ["        <note>"]
        if chord:
            lines.append("          <chord/>")
        lines.extend(
            [
                "          <pitch>",
                f"          <step>{step}</step>",
                *alter_xml,
                f"          <octave>{octave}</octave>",
                "          </pitch>",
                f"          <duration>{duration}</duration>",
                f"          <voice>{voice}</voice>",
                f"          <type>{note_type}</type>",
            ]
        )
        lines.extend(["          <dot/>"] * dots)
        lines.extend(accidental_xml)
        lines.extend([f"          <staff>{staff}</staff>", "        </note>"])
        return lines

    @staticmethod
    def _attributes_xml(key: str, time: dict[str, Any], two_staff: bool) -> str:
        fifths = RuleBasedGenerator._key_fifths(key)
        mode = "minor" if "minor" in key.lower() else "major"
        clefs = (
            [
                "          <staves>2</staves>",
                "          <clef number=\"1\">",
                "            <sign>G</sign>",
                "            <line>2</line>",
                "          </clef>",
                "          <clef number=\"2\">",
                "            <sign>F</sign>",
                "            <line>4</line>",
                "          </clef>",
            ]
            if two_staff
            else [
                "          <clef>",
                "            <sign>G</sign>",
                "            <line>2</line>",
                "          </clef>",
            ]
        )
        return "\n".join(
            [
                "        <attributes>",
                f"          <divisions>{time['divisions']}</divisions>",
                "          <key>",
                f"            <fifths>{fifths}</fifths>",
                f"            <mode>{mode}</mode>",
                "          </key>",
                "          <time>",
                f"            <beats>{time['beats']}</beats>",
                f"            <beat-type>{time['beat_type']}</beat-type>",
                "          </time>",
                *clefs,
                "        </attributes>",
            ]
        )

    @staticmethod
    def _key_fifths(key: str) -> int:
        fifths = {
            "C": 0,
            "G": 1,
            "D": 2,
            "A": 3,
            "E": 4,
            "B": 5,
            "F#": 6,
            "F": -1,
            "Bb": -2,
            "Eb": -3,
            "Ab": -4,
            "Db": -5,
        }
        tonic = RuleBasedGenerator._tonic(key)
        value = fifths.get(tonic, 0)
        if "minor" in key.lower():
            return value - 3
        return value

    @staticmethod
    def _abc_note(note_name: str) -> str:
        step, alter, octave = RuleBasedGenerator._parse_pitch_name(note_name)
        prefix = "^" if alter == 1 else "_" if alter == -1 else ""
        if octave >= 5:
            return f"{prefix}{step.lower()}"
        return f"{prefix}{step}"

    @staticmethod
    def _abc_key(key: str) -> str:
        tonic = RuleBasedGenerator._tonic(key)
        return tonic + ("m" if "minor" in key.lower() else "")

"""MusicXML statistics used by Sera V0.5 diagnostics and metrics.

The parser is intentionally lightweight. It reads the subset of MusicXML that
Sera emits today and degrades to conservative defaults for external corpora.
"""

from __future__ import annotations

import csv
import json
import math
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any
import xml.etree.ElementTree as ET


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


@dataclass(slots=True)
class ParsedNote:
    """A normalized MusicXML note/rest event."""

    measure: int
    offset_quarter: float
    duration_quarter: float
    duration_name: str
    midi: int | None
    pitch: str
    is_rest: bool = False
    is_chord_tone: bool = False
    dotted: bool = False
    triplet: bool = False
    staff: str = "1"
    voice: str = "1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_musicxml_text(path: str | Path) -> str:
    """Read plain MusicXML or the first score XML inside an MXL archive."""

    score_path = Path(path)
    if score_path.suffix.lower() != ".mxl":
        return score_path.read_text(encoding="utf-8", errors="ignore")
    with zipfile.ZipFile(score_path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith((".xml", ".musicxml"))]
        if not names:
            return ""
        return archive.read(names[0]).decode("utf-8", errors="ignore")


def iter_musicxml_paths(input_dir: str | Path, max_files: int = 0) -> list[Path]:
    """Return MusicXML-like files below a directory."""

    root = Path(input_dir)
    if root.is_file():
        return [root]
    paths: list[Path] = []
    for pattern in ("*.musicxml", "*.xml", "*.mxl"):
        paths.extend(root.rglob(pattern))
    unique = sorted(set(paths))
    return unique[:max_files] if max_files else unique


def pitch_to_midi(step: str, alter: int, octave: int) -> int:
    """Convert MusicXML pitch fields to a MIDI number."""

    return (octave + 1) * 12 + STEP_TO_SEMITONE.get(step.upper(), 0) + alter


def midi_to_pitch(midi: int) -> str:
    """Return a compact pitch name such as C4 or F#5."""

    octave = midi // 12 - 1
    step, alter = SEMITONE_TO_STEP[midi % 12]
    accidental = "#" if alter > 0 else "b" if alter < 0 else ""
    return f"{step}{accidental}{octave}"


def parse_pitch_name(pitch: str) -> int | None:
    """Parse a compact pitch name to MIDI."""

    if not pitch or len(pitch) < 2:
        return None
    step = pitch[0].upper()
    if step not in STEP_TO_SEMITONE:
        return None
    rest = pitch[1:]
    alter = 0
    if rest.startswith("#"):
        alter = 1
        rest = rest[1:]
    elif rest.startswith("b"):
        alter = -1
        rest = rest[1:]
    try:
        octave = int(rest)
    except ValueError:
        return None
    return pitch_to_midi(step, alter, octave)


def duration_name(duration_quarter: float, dotted: bool = False, is_rest: bool = False) -> str:
    """Map quarter-note units to a readable duration name."""

    prefix = "rest_" if is_rest else ""
    if dotted or math.isclose(duration_quarter, 1.5, abs_tol=0.02):
        return f"{prefix}dotted_quarter"
    mapping = [
        (0.25, "sixteenth"),
        (0.5, "eighth"),
        (1.0, "quarter"),
        (2.0, "half"),
        (3.0, "dotted_half"),
        (4.0, "whole"),
    ]
    for value, name in mapping:
        if math.isclose(duration_quarter, value, abs_tol=0.02):
            return f"{prefix}{name}"
    return f"{prefix}other"


def parse_musicxml_notes(musicxml: str) -> list[ParsedNote]:
    """Extract ordered note/rest events from MusicXML text."""

    if not musicxml.strip():
        return []
    root = ET.fromstring(musicxml)
    divisions = 1
    notes: list[ParsedNote] = []
    for measure_index, measure in enumerate(root.findall(".//measure"), start=1):
        attr = measure.find("attributes")
        if attr is not None:
            divisions = _int_text(attr.find("divisions"), divisions)
            divisions = max(1, divisions)
        voice_offsets: dict[tuple[str, str], float] = {}
        for note in measure.findall("note"):
            duration = _int_text(note.find("duration"), 0)
            duration_quarter = duration / divisions if divisions else float(duration)
            staff = note.findtext("staff") or "1"
            voice = note.findtext("voice") or "1"
            key = (staff, voice)
            is_chord = note.find("chord") is not None
            offset = voice_offsets.get(key, 0.0)
            if is_chord:
                offset = offset - duration_quarter
            is_rest = note.find("rest") is not None
            pitch_node = note.find("pitch")
            midi: int | None = None
            pitch = "REST"
            if pitch_node is not None:
                step = (pitch_node.findtext("step") or "C").strip().upper()
                alter = _int_text(pitch_node.find("alter"), 0)
                octave = _int_text(pitch_node.find("octave"), 4)
                midi = pitch_to_midi(step, alter, octave)
                pitch = _musicxml_pitch_name(step, alter, octave)
            dotted = note.find("dot") is not None
            triplet = note.find("time-modification") is not None
            notes.append(
                ParsedNote(
                    measure=int(measure.get("number") or measure_index),
                    offset_quarter=round(offset, 4),
                    duration_quarter=round(duration_quarter, 4),
                    duration_name=duration_name(duration_quarter, dotted=dotted, is_rest=is_rest),
                    midi=midi,
                    pitch=pitch,
                    is_rest=is_rest,
                    is_chord_tone=is_chord,
                    dotted=dotted,
                    triplet=triplet,
                    staff=staff,
                    voice=voice,
                )
            )
            if not is_chord:
                voice_offsets[key] = voice_offsets.get(key, 0.0) + duration_quarter
    return sorted(notes, key=lambda item: (item.measure, item.offset_quarter, item.staff, item.voice, item.is_chord_tone))


def analyze_musicxml(musicxml: str, source: str = "") -> dict[str, Any]:
    """Return V0.5 rhythm, melody, phrase, and failure-mode statistics."""

    notes = parse_musicxml_notes(musicxml)
    pitched = [note for note in notes if note.midi is not None and not note.is_chord_tone]
    rhythm = rhythm_distribution(notes)
    intervals = interval_distribution(pitched)
    contour = melody_contour(pitched)
    complexity = rhythm_complexity(notes)
    phrase = phrase_metrics(pitched, notes)
    failures = failure_modes(notes, pitched, rhythm, intervals, phrase)
    return {
        "source": source,
        "note_count": len(notes),
        "pitched_note_count": len(pitched),
        "measure_count": len({note.measure for note in notes}),
        "rhythm_distribution": rhythm,
        "pitch_interval_distribution": intervals,
        "melody_contour": contour,
        "rhythm_complexity": complexity,
        "phrase_metrics": phrase,
        "failure_modes": failures,
    }


def rhythm_distribution(notes: list[ParsedNote]) -> dict[str, float]:
    """Compute requested rhythm ratios."""

    total = max(1, len(notes))
    rests = [note for note in notes if note.is_rest]
    syncopated = [note for note in notes if _is_syncopated(note)]
    return {
        "quarter_note_ratio": _duration_ratio(notes, "quarter"),
        "eighth_note_ratio": _duration_ratio(notes, "eighth"),
        "sixteenth_note_ratio": _duration_ratio(notes, "sixteenth"),
        "dotted_rhythm_ratio": sum(1 for note in notes if note.dotted or "dotted" in note.duration_name) / total,
        "triplet_ratio": sum(1 for note in notes if note.triplet) / total,
        "rest_ratio": len(rests) / total,
        "syncopation_ratio": len(syncopated) / total,
    }


def interval_distribution(pitched: list[ParsedNote]) -> dict[str, float | int]:
    """Compute interval ratios between adjacent melody events."""

    intervals = [b.midi - a.midi for a, b in zip(pitched, pitched[1:], strict=False) if a.midi is not None and b.midi is not None]
    total = max(1, len(intervals))
    abs_values = [abs(interval) for interval in intervals]
    return {
        "same_pitch_ratio": sum(1 for interval in abs_values if interval == 0) / total,
        "stepwise_second_ratio": sum(1 for interval in abs_values if interval in {1, 2}) / total,
        "third_leap_ratio": sum(1 for interval in abs_values if interval in {3, 4}) / total,
        "fourth_plus_leap_ratio": sum(1 for interval in abs_values if interval >= 5) / total,
        "ascending_ratio": sum(1 for interval in intervals if interval > 0) / total,
        "descending_ratio": sum(1 for interval in intervals if interval < 0) / total,
        "max_leap": max(abs_values) if abs_values else 0,
        "average_interval_size": mean(abs_values) if abs_values else 0.0,
    }


def melody_contour(pitched: list[ParsedNote]) -> str:
    """Classify a melody contour into the V0.5 buckets."""

    midis = [note.midi for note in pitched if note.midi is not None]
    if len(midis) < 3 or max(midis, default=0) - min(midis, default=0) <= 2:
        return "static"
    first = midis[0]
    last = midis[-1]
    midpoint = midis[len(midis) // 2]
    top = max(midis)
    direction_changes = _direction_changes(midis)
    up = sum(1 for a, b in zip(midis, midis[1:], strict=False) if b > a)
    down = sum(1 for a, b in zip(midis, midis[1:], strict=False) if b < a)
    if midpoint == top and midpoint > first and midpoint > last:
        return "arch"
    if direction_changes >= 2:
        return "wave"
    if up > down * 1.5 and last > first:
        return "ascending"
    if down > up * 1.5 and last < first:
        return "descending"
    return "wave"


def rhythm_complexity(notes: list[ParsedNote]) -> dict[str, float | int]:
    """Return duration diversity and repetition statistics."""

    names = [note.duration_name for note in notes]
    counts = Counter(names)
    entropy = _entropy(counts.values())
    measures = max(1, len({note.measure for note in notes}))
    return {
        "unique_duration_count": len(counts),
        "rhythmic_entropy": entropy,
        "average_notes_per_bar": len(notes) / measures,
        "max_consecutive_same_duration": _max_consecutive(names),
        "quarter_note_dominance_score": counts.get("quarter", 0) / max(1, len(names)),
    }


def phrase_metrics(pitched: list[ParsedNote], notes: list[ParsedNote]) -> dict[str, float | int]:
    """Estimate phrase, cadence, repetition, and motif recurrence."""

    measures = sorted({note.measure for note in notes})
    measure_count = len(measures)
    phrase_length = 4 if measure_count >= 4 else max(1, measure_count)
    phrase_end_notes = _phrase_end_notes(pitched, phrase_length)
    cadence_hits = sum(1 for note in phrase_end_notes if _cadence_like(note, pitched))
    motifs = _motif_counter(pitched, size=3)
    recurring = sum(count for count in motifs.values() if count > 1)
    exact_repeats = sum(
        1
        for a, b in zip(pitched, pitched[1:], strict=False)
        if a.midi == b.midi and math.isclose(a.duration_quarter, b.duration_quarter, abs_tol=0.02)
    )
    return {
        "phrase_length_estimate": phrase_length,
        "cadence_like_ending_ratio": cadence_hits / max(1, len(phrase_end_notes)),
        "repetition_ratio": exact_repeats / max(1, len(pitched) - 1),
        "motif_recurrence_ratio": recurring / max(1, sum(motifs.values())),
    }


def failure_modes(
    notes: list[ParsedNote],
    pitched: list[ParsedNote],
    rhythm: dict[str, float],
    intervals: dict[str, float | int],
    phrase: dict[str, float | int],
) -> dict[str, bool]:
    """Flag common V0.4 collapse modes."""

    midis = [note.midi for note in pitched if note.midi is not None]
    return {
        "too_many_consecutive_quarters": _max_consecutive([note.duration_name for note in notes]) > 3
        and rhythm.get("quarter_note_ratio", 0.0) >= 0.55,
        "too_many_same_direction_steps": _max_same_direction_step_run(midis) > 4,
        "narrow_pitch_range": (max(midis) - min(midis) if midis else 0) < 7,
        "missing_cadence": float(phrase.get("cadence_like_ending_ratio", 0.0)) < 0.25,
        "identical_bar_rhythm": _has_identical_bar_rhythm(notes),
    }


def aggregate_analyses(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Average nested analysis rows for dataset-level reports."""

    if not rows:
        return {"file_count": 0}
    nested_keys = [
        "rhythm_distribution",
        "pitch_interval_distribution",
        "rhythm_complexity",
        "phrase_metrics",
        "failure_modes",
    ]
    summary: dict[str, Any] = {"file_count": len(rows)}
    for key in nested_keys:
        subkeys = sorted({subkey for row in rows for subkey in row.get(key, {})})
        summary[key] = {
            subkey: sum(float(row.get(key, {}).get(subkey, 0.0)) for row in rows) / len(rows)
            for subkey in subkeys
        }
    contours = Counter(str(row.get("melody_contour", "static")) for row in rows)
    summary["melody_contour_distribution"] = {
        contour: count / len(rows) for contour, count in sorted(contours.items())
    }
    return summary


def write_distribution_csv(path: str | Path, rows: list[dict[str, Any]], nested_key: str) -> None:
    """Write a flat CSV for one nested distribution field."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    subkeys = sorted({key for row in rows for key in row.get(nested_key, {})})
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", *subkeys])
        writer.writeheader()
        for row in rows:
            payload = {"source": row.get("source", "")}
            payload.update({key: row.get(nested_key, {}).get(key, 0.0) for key in subkeys})
            writer.writerow(payload)


def diagnose_directory(input_dir: str | Path, output_json: str | Path, max_files: int = 0) -> dict[str, Any]:
    """Analyze a directory and write a JSON report."""

    analyses: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for path in iter_musicxml_paths(input_dir, max_files=max_files):
        try:
            analyses.append(analyze_musicxml(read_musicxml_text(path), source=str(path)))
        except Exception as exc:  # noqa: BLE001 - diagnostics should continue.
            failures.append({"source": str(path), "error": str(exc)})
    report = {
        "input_dir": str(input_dir),
        "summary": aggregate_analyses(analyses),
        "files": analyses,
        "failures": failures,
    }
    target = Path(output_json)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _musicxml_pitch_name(step: str, alter: int, octave: int) -> str:
    accidental = "#" * int(alter) if int(alter) > 0 else "b" * abs(int(alter)) if int(alter) < 0 else ""
    return f"{step.upper()}{accidental}{int(octave)}"


def _int_text(node: ET.Element | None, fallback: int) -> int:
    if node is None or node.text is None:
        return fallback
    try:
        return int(float(node.text.strip()))
    except ValueError:
        return fallback


def _duration_ratio(notes: list[ParsedNote], name: str) -> float:
    return sum(1 for note in notes if note.duration_name == name) / max(1, len(notes))


def _is_syncopated(note: ParsedNote) -> bool:
    if note.is_rest:
        return False
    fractional = note.offset_quarter - math.floor(note.offset_quarter)
    return math.isclose(fractional, 0.5, abs_tol=0.02) and note.duration_quarter >= 0.5


def _entropy(values: Any) -> float:
    total = sum(values)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in values:
        if value:
            p = value / total
            entropy -= p * math.log2(p)
    return entropy


def _max_consecutive(values: list[str]) -> int:
    best = 0
    current = 0
    previous = object()
    for value in values:
        if value == previous:
            current += 1
        else:
            current = 1
            previous = value
        best = max(best, current)
    return best


def _direction_changes(midis: list[int]) -> int:
    signs: list[int] = []
    for a, b in zip(midis, midis[1:], strict=False):
        diff = b - a
        if diff:
            signs.append(1 if diff > 0 else -1)
    return sum(1 for a, b in zip(signs, signs[1:], strict=False) if a != b)


def _phrase_end_notes(pitched: list[ParsedNote], phrase_length: int) -> list[ParsedNote]:
    if not pitched:
        return []
    ends: list[ParsedNote] = []
    for measure in sorted({note.measure for note in pitched}):
        if measure % phrase_length == 0:
            candidates = [note for note in pitched if note.measure == measure]
            if candidates:
                ends.append(candidates[-1])
    if pitched[-1] not in ends:
        ends.append(pitched[-1])
    return ends


def _cadence_like(note: ParsedNote, pitched: list[ParsedNote]) -> bool:
    if note.midi is None or not pitched:
        return False
    first_pc = pitched[0].midi % 12 if pitched[0].midi is not None else 0
    final_pc = note.midi % 12
    if final_pc in {first_pc, (first_pc + 7) % 12, (first_pc + 11) % 12}:
        return True
    try:
        index = pitched.index(note)
    except ValueError:
        return False
    if index <= 0 or pitched[index - 1].midi is None:
        return False
    approach = abs(note.midi - pitched[index - 1].midi) % 12
    return approach in {4, 5, 7} and note.duration_quarter >= 1.0


def _motif_counter(pitched: list[ParsedNote], size: int) -> Counter[tuple[int, ...]]:
    midis = [note.midi for note in pitched if note.midi is not None]
    return Counter(tuple(midis[index : index + size]) for index in range(0, max(0, len(midis) - size + 1)))


def _max_same_direction_step_run(midis: list[int]) -> int:
    best = 0
    current = 0
    direction = 0
    for a, b in zip(midis, midis[1:], strict=False):
        diff = b - a
        new_direction = 1 if diff > 0 else -1 if diff < 0 else 0
        if abs(diff) in {1, 2} and new_direction:
            current = current + 1 if new_direction == direction else 1
            direction = new_direction
        else:
            current = 0
            direction = 0
        best = max(best, current)
    return best


def _has_identical_bar_rhythm(notes: list[ParsedNote]) -> bool:
    by_measure: dict[int, tuple[str, ...]] = {}
    for measure in sorted({note.measure for note in notes}):
        by_measure[measure] = tuple(note.duration_name for note in notes if note.measure == measure and not note.is_chord_tone)
    patterns = list(by_measure.values())
    if len(patterns) < 2:
        return False
    return len(set(patterns)) == 1

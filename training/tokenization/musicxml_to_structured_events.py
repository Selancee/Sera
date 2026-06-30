"""Convert MusicXML into Sera V0.5 structured event tokens."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from evaluation.analysis.music_statistics import parse_musicxml_notes, read_musicxml_text
from training.tokenization.structured_events import (
    StructuredEventSequence,
    cadence_token,
    dynamic_token,
    harmony_token,
    key_token,
    meter_token,
    motif_token,
    note_token,
    position_token,
    rhythm_token,
    section_token,
    tempo_token,
    texture_token,
)


DEFAULT_MAJOR_PROGRESSION = ["I", "vi", "IV", "V"]
DEFAULT_MINOR_PROGRESSION = ["i", "VI", "iv", "V"]


def musicxml_to_structured_events(text: str, source: str = "") -> StructuredEventSequence:
    """Convert one MusicXML string to structured event tokens."""

    root = ET.fromstring(text)
    key = _extract_key(root)
    meter = _extract_meter(root)
    tempo = _extract_tempo(root)
    mode = "minor" if "minor" in key.lower() else "major"
    progression = DEFAULT_MINOR_PROGRESSION if mode == "minor" else DEFAULT_MAJOR_PROGRESSION
    notes = parse_musicxml_notes(text)
    measures = sorted({note.measure for note in notes}) or [1]
    measure_count = len(measures)
    events = [
        key_token(key),
        meter_token(meter),
        tempo_token(tempo),
        dynamic_token("mf"),
        texture_token("melody"),
        section_token("A"),
        "PHRASE_START",
    ]

    for measure in measures:
        if measure > 1 and (measure - 1) % 8 == 0:
            events.append(section_token(chr(ord("A") + ((measure - 1) // 8))))
        if measure > 1 and (measure - 1) % 4 == 0:
            events.append("PHRASE_START")
        cadence = "authentic" if measure == measures[-1] else "half" if measure % 4 == 0 else "none"
        events.extend(
            [
                "BAR",
                harmony_token(progression[(measure - 1) % len(progression)]),
                cadence_token(cadence),
                motif_token("A", variation=measure > 4),
            ]
        )
        measure_notes = [
            note
            for note in notes
            if note.measure == measure and not note.is_chord_tone and str(note.staff) == "1"
        ]
        for note in measure_notes:
            events.append(position_token(note.offset_quarter))
            events.append(rhythm_token(note.duration_name, is_rest=note.is_rest))
            if note.is_rest:
                continue
            events.append(note_token(note.pitch))
        if measure % 4 == 0 or measure == measures[-1]:
            events.append("PHRASE_END")
    events.append("END")
    return StructuredEventSequence(
        events=events,
        metadata={
            "source": source,
            "key": key,
            "meter": meter,
            "tempo": tempo,
            "measure_count": measure_count,
            "event_count": len(events),
        },
    )


def convert_paths(paths: list[Path], output_path: Path, report_path: Path) -> dict:
    """Convert multiple MusicXML files and write JSONL plus tokenization report."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    successes: list[dict] = []
    failures: list[dict] = []
    with output_path.open("w", encoding="utf-8") as handle:
        for path in paths:
            try:
                sequence = musicxml_to_structured_events(read_musicxml_text(path), source=str(path))
                handle.write(
                    json.dumps(
                        {
                            "source": str(path),
                            "events": sequence.events,
                            "metadata": sequence.metadata,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                successes.append(sequence.metadata)
            except Exception as exc:  # noqa: BLE001 - tokenization should continue.
                failures.append({"source": str(path), "error": str(exc)})
    report = {
        "output_path": str(output_path),
        "success_count": len(successes),
        "failure_count": len(failures),
        "successes": successes,
        "failures": failures,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _extract_key(root: ET.Element) -> str:
    key_node = root.find(".//key")
    fifths = int((key_node.findtext("fifths") if key_node is not None else "0") or 0)
    mode = (key_node.findtext("mode") if key_node is not None else "major") or "major"
    major = {0: "C", 1: "G", 2: "D", 3: "A", 4: "E", -1: "F", -2: "Bb", -3: "Eb"}
    minor = {-3: "A", -2: "E", -1: "B", 0: "C", 1: "G", 2: "D", 3: "A"}
    tonic = (minor if mode == "minor" else major).get(fifths, "C")
    return f"{tonic} {mode}"


def _extract_meter(root: ET.Element) -> str:
    time = root.find(".//time")
    if time is None:
        return "4/4"
    return f"{time.findtext('beats') or '4'}/{time.findtext('beat-type') or '4'}"


def _extract_tempo(root: ET.Element) -> int:
    sound = root.find(".//sound")
    if sound is not None and sound.get("tempo"):
        try:
            return int(float(sound.get("tempo") or "72"))
        except ValueError:
            return 72
    return 72


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="examples/scores")
    parser.add_argument("--output", default="data/tokenized_v05/structured_events.jsonl")
    parser.add_argument("--report", default="data/tokenized_v05/tokenization_report.json")
    parser.add_argument("--max_files", type=int, default=0)
    args = parser.parse_args()
    root = Path(args.input_dir)
    paths = sorted(set(root.rglob("*.musicxml")) | set(root.rglob("*.xml")) | set(root.rglob("*.mxl")))
    if args.max_files:
        paths = paths[: args.max_files]
    report = convert_paths(paths, Path(args.output), Path(args.report))
    print(f"Tokenized {report['success_count']} files; failures={report['failure_count']}")


if __name__ == "__main__":
    main()

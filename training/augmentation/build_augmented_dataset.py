"""Build V0.5 augmented MusicXML and fragment datasets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.analysis.music_statistics import iter_musicxml_paths, read_musicxml_text
from training.augmentation.cadence_augmentation import augment_cadence_events
from training.augmentation.motif_augmentation import augment_motif_events
from training.augmentation.rhythm_augmentation import augment_rhythm_events
from training.augmentation.transpose_augmentation import target_keys_for_source, transpose_musicxml_text
from training.tokenization.musicxml_to_structured_events import musicxml_to_structured_events
from training.tokenization.structured_events_to_musicxml import structured_events_to_musicxml


def build_augmented_dataset(args: argparse.Namespace) -> dict:
    """CLI implementation for V0.5 augmentation."""

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    fragments_dir = Path(args.fragments_dir)
    tokenized_dir = Path(args.tokenized_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fragments_dir.mkdir(parents=True, exist_ok=True)
    tokenized_dir.mkdir(parents=True, exist_ok=True)
    paths = iter_musicxml_paths(input_dir, max_files=args.max_files)
    failures: list[dict] = []
    metadata_rows: list[dict] = []
    tokenized_rows: list[dict] = []
    enable_all = not any([args.transpose, args.rhythm, args.motif, args.cadence, args.fragment])

    for path in paths:
        try:
            text = read_musicxml_text(path)
            sequence = musicxml_to_structured_events(text, source=str(path))
            tokenized_rows.append({"source": str(path), "events": sequence.events, "metadata": sequence.metadata})
            source_key = str(sequence.metadata.get("key", "C major"))
            if args.transpose or enable_all:
                for target_key in target_keys_for_source(source_key):
                    xml, meta = transpose_musicxml_text(text, target_key)
                    metadata_rows.append(_write_sample(output_dir, path, xml, meta, suffix=f"transpose_{target_key.replace(' ', '_')}"))
            if args.rhythm or enable_all:
                events, meta = augment_rhythm_events(sequence.events)
                metadata_rows.append(_write_sample(output_dir, path, structured_events_to_musicxml(events), meta, suffix="rhythm"))
            if args.motif or enable_all:
                for strategy in ["repeat", "sequence_up", "sequence_down", "inversion", "rhythmic_variation", "ending_variation"]:
                    events, meta = augment_motif_events(sequence.events, strategy)
                    metadata_rows.append(_write_sample(output_dir, path, structured_events_to_musicxml(events), meta, suffix=f"motif_{strategy}"))
            if args.cadence or enable_all:
                for cadence_type in ["half", "authentic", "deceptive", "plagal"]:
                    events, meta = augment_cadence_events(sequence.events, cadence_type)
                    metadata_rows.append(_write_sample(output_dir, path, structured_events_to_musicxml(events), meta, suffix=f"cadence_{cadence_type}"))
            if args.fragment or enable_all:
                metadata_rows.extend(_write_fragments(fragments_dir, path, sequence.events, sequence.metadata))
        except Exception as exc:  # noqa: BLE001 - keep batch augmentation going.
            failures.append({"source": str(path), "error": str(exc)})

    (output_dir / "metadata.json").write_text(json.dumps(metadata_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "augmentation_failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    tokenized_path = tokenized_dir / "structured_events.jsonl"
    with tokenized_path.open("w", encoding="utf-8") as handle:
        for row in tokenized_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    report = {
        "input_files": len(paths),
        "augmented_samples": len(metadata_rows),
        "failures": len(failures),
        "output_dir": str(output_dir),
        "fragments_dir": str(fragments_dir),
        "tokenized_events": str(tokenized_path),
    }
    (output_dir / "augmentation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _write_sample(output_dir: Path, source: Path, musicxml: str, metadata: dict, suffix: str) -> dict:
    stem = f"{source.stem}_{suffix}"
    xml_path = output_dir / f"{stem}.musicxml"
    meta_path = output_dir / f"{stem}.metadata.json"
    payload = {
        "source": str(source),
        "output": str(xml_path),
        "metadata_path": str(meta_path),
        "augmentation_method": metadata.get("augmentation", suffix),
        "key": metadata.get("target_key", metadata.get("source_key", "")),
        "meter": metadata.get("meter", "4/4"),
        "length": metadata.get("length", ""),
        **metadata,
    }
    xml_path.write_text(musicxml, encoding="utf-8")
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _write_fragments(output_dir: Path, source: Path, events: list[str], metadata: dict) -> list[dict]:
    bars = _split_bars(events)
    rows: list[dict] = []
    for size in [1, 2, 4, 8]:
        for start in range(0, len(bars), size):
            chunk = bars[start : start + size]
            if len(chunk) != size:
                continue
            chunk_events = [event for bar in chunk for event in bar] + ["END"]
            xml = structured_events_to_musicxml(chunk_events, title=f"{source.stem} fragment {size}")
            rows.append(_write_sample(output_dir, source, xml, {"augmentation": "fragment", "length": size, **metadata}, suffix=f"fragment_{size}_{start + 1}"))
    return rows


def _split_bars(events: list[str]) -> list[list[str]]:
    bars: list[list[str]] = []
    current: list[str] = []
    prefix = [token for token in events if token.startswith(("KEY_", "METER_", "TEMPO_"))]
    for token in events:
        if token == "BAR":
            if current:
                bars.append(current)
            current = [*prefix, "BAR"]
        elif token == "END":
            continue
        elif current:
            current.append(token)
    if current:
        bars.append(current)
    return bars


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="examples/scores")
    parser.add_argument("--output_dir", default="data/augmented")
    parser.add_argument("--fragments_dir", default="data/fragments")
    parser.add_argument("--tokenized_dir", default="data/tokenized_v05")
    parser.add_argument("--max_files", type=int, default=0)
    parser.add_argument("--transpose", action="store_true")
    parser.add_argument("--rhythm", action="store_true")
    parser.add_argument("--motif", action="store_true")
    parser.add_argument("--cadence", action="store_true")
    parser.add_argument("--fragment", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build_augmented_dataset(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

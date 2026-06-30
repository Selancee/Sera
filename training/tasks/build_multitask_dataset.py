"""Build Sera V0.5 multitask local-symbolic dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from evaluation.analysis.music_statistics import iter_musicxml_paths, read_musicxml_text
from training.tasks.cadence_generation_task import build_cadence_generation_examples
from training.tasks.melody_fragment_task import build_melody_fragment_examples
from training.tasks.motif_variation_task import build_motif_variation_examples
from training.tasks.rhythm_rewrite_task import build_rhythm_rewrite_examples
from training.tokenization.musicxml_to_structured_events import musicxml_to_structured_events


TASK_BUILDERS = [
    build_melody_fragment_examples,
    build_motif_variation_examples,
    build_cadence_generation_examples,
    build_rhythm_rewrite_examples,
]


def build_multitask_dataset(
    input_dirs: list[str | Path],
    output_path: str | Path = "data/tokenized_v05/multitask_dataset.jsonl",
    max_files: int = 0,
) -> dict:
    """Scan MusicXML files and write multitask JSONL examples."""

    paths: list[Path] = []
    for input_dir in input_dirs:
        paths.extend(iter_musicxml_paths(input_dir))
    paths = sorted(set(paths))
    if max_files:
        paths = paths[:max_files]
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    failures: list[dict] = []
    total = 0
    with target.open("w", encoding="utf-8") as handle:
        for path in paths:
            try:
                sequence = musicxml_to_structured_events(read_musicxml_text(path), source=str(path))
                for builder in TASK_BUILDERS:
                    for example in builder(sequence.events, sequence.metadata):
                        handle.write(json.dumps(example, ensure_ascii=False) + "\n")
                        counts[str(example["task_type"])] += 1
                        total += 1
            except Exception as exc:  # noqa: BLE001 - dataset build should continue.
                failures.append({"source": str(path), "error": str(exc)})
    report = {
        "input_files": len(paths),
        "examples": total,
        "task_counts": dict(counts),
        "output_path": str(target),
        "failures": failures,
    }
    (target.parent / "multitask_dataset_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dirs", nargs="+", default=["data/fragments", "data/augmented", "examples/scores"])
    parser.add_argument("--output", default="data/tokenized_v05/multitask_dataset.jsonl")
    parser.add_argument("--max_files", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(build_multitask_dataset(args.input_dirs, args.output, args.max_files), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

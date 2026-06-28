"""Build a symbolic dataset index from MusicXML-style corpora.

TODO: Future experiments can point this script at PDMX, MetaScore, POP909, or
Lakh MIDI Dataset derivatives after they have been converted to local
MusicXML/MIDI files.  This script never downloads large datasets itself.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_prompt_lookup(log_path: Path) -> dict[str, str]:
    """Map run ids to prompts from experiment logs."""

    lookup: dict[str, str] = {}
    if not log_path.exists():
        return lookup
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            lookup[str(record.get("run_id"))] = str(record.get("prompt", ""))
    return lookup


def iter_score_paths(source_dirs: list[Path]) -> list[Path]:
    """Return MusicXML-like files from local PDMX/MetaScore/MusicXML folders."""

    paths: list[Path] = []
    for source in source_dirs:
        if not source.exists():
            continue
        for pattern in ("*.musicxml", "*.xml"):
            paths.extend(source.rglob(pattern))
        # TODO: add safe .mxl unzip/parse support when compressed corpora are used.
    return sorted(set(paths))


def build_dataset(source_dirs: list[Path], log_path: Path, out_path: Path) -> int:
    """Write JSONL examples with prompt, run id, source, and raw MusicXML."""

    lookup = load_prompt_lookup(log_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8") as handle:
        for score_path in iter_score_paths(source_dirs):
            run_id = score_path.stem
            example = {
                "run_id": run_id,
                "prompt": lookup.get(run_id, ""),
                "musicxml": score_path.read_text(encoding="utf-8"),
                "source": str(score_path),
            }
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["examples/scores"],
        help="Local MusicXML/PDMX/MetaScore-derived folders to scan.",
    )
    parser.add_argument("--logs", default="data/metadata/experiment_logs.jsonl")
    parser.add_argument("--out", default="data/processed/musicxml_dataset.jsonl")
    args = parser.parse_args()
    count = build_dataset([Path(item) for item in args.sources], Path(args.logs), Path(args.out))
    print(f"Wrote {count} examples to {args.out}")


if __name__ == "__main__":
    main()

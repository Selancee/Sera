"""Build a symbolic dataset index from MusicXML-style corpora.

TODO: Future experiments can point this script at PDMX, MetaScore, POP909, or
Lakh MIDI Dataset derivatives after they have been converted to local
MusicXML/MIDI files.  This script never downloads large datasets itself.
"""

from __future__ import annotations

import json
import argparse
import zipfile
from hashlib import sha1
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
        for pattern in ("*.musicxml", "*.xml", "*.mxl"):
            paths.extend(source.rglob(pattern))
    return sorted(set(paths))


def read_score_text(score_path: Path) -> str:
    """Read plain MusicXML or the first XML score inside a compressed MXL."""

    if score_path.suffix.lower() != ".mxl":
        return score_path.read_text(encoding="utf-8", errors="ignore")
    with zipfile.ZipFile(score_path) as archive:
        xml_names = [name for name in archive.namelist() if name.lower().endswith((".xml", ".musicxml"))]
        if not xml_names:
            return ""
        return archive.read(xml_names[0]).decode("utf-8", errors="ignore")


def build_dataset(source_dirs: list[Path], log_path: Path, out_path: Path, max_examples: int = 0) -> int:
    """Write JSONL examples with prompt, run id, source, and raw MusicXML."""

    lookup = load_prompt_lookup(log_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    seen_hashes: set[str] = set()
    with out_path.open("w", encoding="utf-8") as handle:
        for score_path in iter_score_paths(source_dirs):
            musicxml = read_score_text(score_path)
            if not musicxml.strip():
                continue
            content_hash = sha1(musicxml.encode("utf-8")).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)
            run_id = score_path.stem
            example = {
                "run_id": run_id,
                "prompt": lookup.get(run_id, ""),
                "musicxml": musicxml,
                "source": str(score_path),
                "sha1": content_hash,
            }
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")
            count += 1
            if max_examples and count >= max_examples:
                break
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
    parser.add_argument("--max-examples", type=int, default=0)
    args = parser.parse_args()
    count = build_dataset(
        [Path(item) for item in args.sources],
        Path(args.logs),
        Path(args.out),
        max_examples=args.max_examples,
    )
    print(f"Wrote {count} examples to {args.out}")


if __name__ == "__main__":
    main()

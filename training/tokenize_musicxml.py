"""Tokenize MusicXML into a simple symbolic text/intermediate JSON format.

TODO: Replace this regex tokenizer with a musically aware event vocabulary
covering part, measure, pitch, duration, tie, articulation, harmony, and form.
Future data sources can include PDMX, MetaScore, POP909, and Lakh MIDI Dataset
after local conversion to MusicXML-like symbolic files.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TOKEN_PATTERN = re.compile(r"</?[^>]+>|[A-G][#b]?\d|[0-9]+|[A-Za-z_]+")


def tokenize_musicxml(text: str) -> list[str]:
    """Return coarse XML/music tokens."""

    return TOKEN_PATTERN.findall(text)


def musicxml_to_intermediate_json(text: str) -> dict[str, object]:
    """Return a minimal intermediate representation for decoder training."""

    tokens = tokenize_musicxml(text)
    return {"tokens": tokens, "token_count": len(tokens)}


def tokenize_dataset(dataset_path: Path, out_path: Path) -> int:
    """Tokenize a JSONL dataset into prompt-token pairs."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with dataset_path.open("r", encoding="utf-8") as source, out_path.open("w", encoding="utf-8") as target:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            target.write(
                json.dumps(
                    {
                        "run_id": row.get("run_id"),
                        "prompt": row.get("prompt", ""),
                        **musicxml_to_intermediate_json(row.get("musicxml", "")),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            count += 1
    return count


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/processed/musicxml_dataset.jsonl")
    parser.add_argument("--out", default="data/processed/musicxml_tokens.jsonl")
    args = parser.parse_args()
    count = tokenize_dataset(Path(args.dataset), Path(args.out))
    print(f"Wrote {count} tokenized examples to {args.out}")


if __name__ == "__main__":
    main()

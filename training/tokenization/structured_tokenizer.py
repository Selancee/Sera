"""Tokenizer helpers for V0.5 structured event and multitask datasets."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


SPECIAL_TOKENS = ["<pad>", "<bos>", "<eos>", "<unk>", "<input>", "<target>"]


class StructuredTokenizer:
    """A tiny deterministic vocabulary for structured event tokens."""

    def __init__(self, vocab: dict[str, int] | None = None) -> None:
        self.vocab = vocab or {token: index for index, token in enumerate(SPECIAL_TOKENS)}

    def fit(self, rows: list[dict], min_frequency: int = 1) -> None:
        counts: Counter[str] = Counter()
        for row in rows:
            counts.update(str(token) for token in row.get("events", []))
            counts.update(str(token) for token in row.get("input_tokens", []))
            counts.update(str(token) for token in row.get("target_tokens", []))
        for token, count in sorted(counts.items()):
            if count >= min_frequency and token not in self.vocab:
                self.vocab[token] = len(self.vocab)

    def encode(self, tokens: list[str]) -> list[int]:
        unk = self.vocab["<unk>"]
        return [self.vocab.get(str(token), unk) for token in tokens]

    def decode(self, ids: list[int]) -> list[str]:
        inv = {index: token for token, index in self.vocab.items()}
        return [inv.get(int(index), "<unk>") for index in ids]

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.vocab, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "StructuredTokenizer":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def tokenize_jsonl(input_path: Path, output_path: Path, vocab_path: Path, min_frequency: int = 1) -> dict:
    rows = load_jsonl(input_path)
    tokenizer = StructuredTokenizer()
    tokenizer.fit(rows, min_frequency=min_frequency)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            input_tokens = row.get("input_tokens", row.get("events", []))
            target_tokens = row.get("target_tokens", [])
            payload = dict(row)
            payload["input_ids"] = tokenizer.encode(input_tokens)
            payload["target_ids"] = tokenizer.encode(target_tokens)
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    tokenizer.save(vocab_path)
    return {"rows": len(rows), "vocab_size": len(tokenizer.vocab), "output": str(output_path), "vocab": str(vocab_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/tokenized_v05/multitask_dataset.jsonl")
    parser.add_argument("--output", default="data/tokenized_v05/multitask_token_ids.jsonl")
    parser.add_argument("--vocab", default="data/tokenized_v05/structured_vocab.json")
    parser.add_argument("--min_frequency", type=int, default=1)
    args = parser.parse_args()
    report = tokenize_jsonl(Path(args.input), Path(args.output), Path(args.vocab), args.min_frequency)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

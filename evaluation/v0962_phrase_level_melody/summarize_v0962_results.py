"""Summarize existing V0.96.2 evaluation artifacts."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "results" / "v0962_summary.json"
    if not path.exists():
        raise SystemExit("Run evaluation.v0962_phrase_level_melody.run_v0962_eval first.")
    print(json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

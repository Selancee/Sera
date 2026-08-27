"""Summarize existing V0.96 evaluation artifacts."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "results" / "v096_summary.json"
    if not path.exists():
        raise SystemExit("Run evaluation.v096_expectation_harmony_orchestration.run_v096_eval first.")
    print(json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

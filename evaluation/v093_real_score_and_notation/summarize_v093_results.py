"""Summarize V0.93 evaluation result files."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "evaluation" / "results" / "v093_summary.json"


def main() -> None:
    payload = json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else {}
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

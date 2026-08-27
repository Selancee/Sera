"""Summarize V0.96.1 final-score style integration results."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "evaluation" / "results" / "v0961_summary.json"


def summarize() -> dict:
    if not SUMMARY.exists():
        return {"available": False, "reason": "v0961_summary.json not found"}
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    return {"available": True, **payload}


def main() -> None:
    print(json.dumps(summarize(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

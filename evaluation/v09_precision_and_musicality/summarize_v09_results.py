"""Summarize saved V0.9 benchmark outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from evaluation.v09_precision_and_musicality.metrics import MUSICALITY_COLUMNS, PRECISION_COLUMNS, summarize


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evaluation" / "results"


def main() -> None:
    precision = _read_csv(RESULTS / "v09_precision_results.csv")
    musicality = _read_csv(RESULTS / "v09_musicality_results.csv")
    summary = {
        "precision": summarize(precision, PRECISION_COLUMNS + ["overall_precision_proxy_score"]),
        "musicality": summarize(musicality, MUSICALITY_COLUMNS),
    }
    (RESULTS / "v09_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    main()

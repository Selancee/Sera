"""Summarize saved V0.95 evaluation results."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from evaluation.v095_metadata_melody_line.metrics import MELODY_COLUMNS, METADATA_COLUMNS, summarize
from evaluation.v095_metadata_melody_line.run_v095_eval import latex_table


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evaluation" / "results"


def main() -> None:
    metadata = read_csv(RESULTS / "v095_metadata_results.csv")
    melody = read_csv(RESULTS / "v095_melody_line_results.csv")
    summary = {
        "metadata": summarize(metadata, METADATA_COLUMNS),
        "melody_line": summarize(melody, MELODY_COLUMNS),
        "rows": {"metadata": len(metadata), "melody_line": len(melody)},
    }
    (RESULTS / "v095_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v095_table.tex").write_text(latex_table(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    main()

"""Summarize Sera V0.8 Workbench editing benchmark results."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from evaluation.workbench_editing.workbench_edit_metrics import METRIC_COLUMNS, summarize_rows


ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = ROOT / "evaluation" / "results"


def main() -> None:
    result_path = RESULT_DIR / "workbench_editing_v08_results.csv"
    rows = []
    if result_path.exists():
        with result_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    summary = summarize_rows(rows)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "workbench_editing_v08_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    table = [
        "\\begin{tabular}{lr}",
        "\\toprule",
        "Metric & Score \\\\",
        "\\midrule",
        *[f"{column.replace('_', ' ')} & {summary.get(column, 0):.3f} \\\\" for column in METRIC_COLUMNS],
        "\\bottomrule",
        "\\end{tabular}",
        "",
    ]
    (RESULT_DIR / "workbench_editing_v08_table.tex").write_text("\n".join(table), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


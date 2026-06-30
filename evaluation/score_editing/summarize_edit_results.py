"""Summarize V0.7 score-editing CSV results and write a LaTeX table."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from evaluation.score_editing.edit_metrics import METRIC_KEYS, summarize_rows


def summarize_edit_results(input_csv: str | Path, out_summary: str | Path, out_tex: str | Path) -> dict[str, float]:
    """Summarize score-editing result rows."""

    with Path(input_csv).open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    summary = summarize_rows(rows)
    Path(out_summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["\\begin{tabular}{lr}", "\\toprule", "Metric & Value \\\\", "\\midrule"]
    for key in METRIC_KEYS:
        lines.append(f"{key.replace('_', ' ')} & {summary.get(key, 0.0):.3f} \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    Path(out_tex).write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", default="evaluation/results/score_editing_v07_results.csv")
    parser.add_argument("--out-summary", default="evaluation/results/score_editing_v07_summary.json")
    parser.add_argument("--out-tex", default="evaluation/results/score_editing_v07_table.tex")
    args = parser.parse_args()
    print(json.dumps(summarize_edit_results(args.input_csv, args.out_summary, args.out_tex), indent=2))


if __name__ == "__main__":
    main()

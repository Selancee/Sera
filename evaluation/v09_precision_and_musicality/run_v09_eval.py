"""Run the V0.9 precision and musicality benchmark."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from backend.pipeline import SeraPipeline
from evaluation.v09_precision_and_musicality.metrics import (
    MUSICALITY_COLUMNS,
    PRECISION_COLUMNS,
    musicality_metrics_for_result,
    precision_metrics_for_case,
    summarize,
)


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evaluation" / "results"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-prompts", type=int, default=3)
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    precision_cases = _read_json(Path(__file__).with_name("precision_prompt_sets.json"))[: args.max_prompts]
    musicality_cases = _read_json(Path(__file__).with_name("musicality_prompt_sets.json"))[: args.max_prompts]
    pipeline = SeraPipeline(ROOT)

    precision_rows = [
        {"case_id": case["id"], "prompt": case["prompt"], **precision_metrics_for_case(case)}
        for case in precision_cases
    ]
    musicality_rows: list[dict[str, Any]] = []
    failure_cases: list[dict[str, Any]] = []
    variants = [
        ("v0_8_generator", "hybrid_v05_no_postprocess", {}),
        ("v0_9_rule_based_musicality", "rule_based", {}),
        ("v0_9_hybrid_musicality", "hybrid_v05", {}),
        ("v0_9_postprocessed_model_output", "model", {}),
    ]
    for case in musicality_cases:
        for variant, mode, overrides in variants:
            controls = {**case.get("controls", {}), **overrides}
            result = pipeline.generate(case["prompt"], generator_mode=mode, musicality_controls=controls)
            row = {
                "case_id": case["id"],
                "variant": variant,
                "generator_mode": mode,
                "run_id": result.get("run_id", ""),
                "profile": json.dumps(result.get("metadata", {}).get("generation_profile", {}), ensure_ascii=False),
                **musicality_metrics_for_result(result),
            }
            musicality_rows.append(row)
            if row["accompaniment_presence_rate"] < 1.0 or row["cadence_presence_score"] < 1.0:
                failure_cases.append({"case_id": case["id"], "variant": variant, "row": row})

    _write_csv(RESULTS / "v09_precision_results.csv", precision_rows)
    _write_csv(RESULTS / "v09_musicality_results.csv", musicality_rows)
    summary = {
        "precision": summarize(precision_rows, PRECISION_COLUMNS + ["overall_precision_proxy_score"]),
        "musicality": summarize(musicality_rows, MUSICALITY_COLUMNS),
        "rows": {"precision": len(precision_rows), "musicality": len(musicality_rows)},
    }
    (RESULTS / "v09_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v09_failure_cases.json").write_text(json.dumps(failure_cases, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v09_table.tex").write_text(_latex_table(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _read_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _latex_table(summary: dict[str, Any]) -> str:
    precision = summary["precision"].get("overall_precision_proxy_score", 0.0)
    musicality = summary["musicality"].get("overall_musicality_proxy_score", 0.0)
    return "\\begin{tabular}{lr}\\toprule\nMetric & Score \\\\\n\\midrule\nPrecision proxy & %.3f \\\\\nMusicality proxy & %.3f \\\\\n\\bottomrule\n\\end{tabular}\n" % (precision, musicality)


if __name__ == "__main__":
    main()

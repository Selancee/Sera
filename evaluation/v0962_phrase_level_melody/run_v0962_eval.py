"""Run the V0.96.2 phrase-level melody benchmark."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from backend.pipeline import SeraPipeline
from evaluation.v0962_phrase_level_melody.metrics import baseline_template_metrics, pass_score, phrase_melody_metrics


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evaluation" / "results"


def run(max_prompts: int | None = None) -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    phrase_cases = _load_cases("phrase_melody_cases.json", max_prompts)
    style_cases = _load_cases("style_phrase_cases.json", max_prompts)
    ab_cases = _load_cases("ab_comparison_cases.json", max_prompts)
    pipeline = SeraPipeline(ROOT / "evaluation" / "tmp_v0962_runs")

    phrase_rows = [_run_case(pipeline, case, index) for index, case in enumerate(phrase_cases + style_cases)]
    ab_rows = [_run_ab_case(pipeline, case, index) for index, case in enumerate(ab_cases)]
    failures = [row for row in phrase_rows if not row.get("pass")]
    failures.extend(row for row in ab_rows if float(row.get("improvement", 0.0) or 0.0) <= 0.0)

    _write_csv(RESULTS / "v0962_phrase_melody_results.csv", phrase_rows)
    _write_csv(RESULTS / "v0962_ab_comparison_results.csv", ab_rows)
    summary = {
        "phrase_case_count": len(phrase_rows),
        "ab_case_count": len(ab_rows),
        "average_phrase_proxy": _avg(phrase_rows, "final_score_musicality_proxy"),
        "average_template_baseline_proxy": _avg(ab_rows, "baseline_final_score_musicality_proxy"),
        "average_ab_improvement": _avg(ab_rows, "improvement"),
        "failure_count": len(failures),
    }
    (RESULTS / "v0962_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v0962_failure_cases.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v0962_table.tex").write_text(_latex_table(summary), encoding="utf-8")
    return summary


def _run_case(pipeline: SeraPipeline, case: dict[str, Any], index: int) -> dict[str, Any]:
    result = pipeline.generate(
        str(case["prompt"]),
        generator_mode="rule_based",
        musicality_controls={"variation_seed": f"v0962-eval-{case['case_id']}-{index}"},
        candidate_count=3,
    )
    metrics = phrase_melody_metrics(result, expected_style=str(case.get("style", "")))
    row = {
        "case_id": case["case_id"],
        "style": case.get("style", ""),
        **metrics,
    }
    row["pass"] = pass_score(row)
    return row


def _run_ab_case(pipeline: SeraPipeline, case: dict[str, Any], index: int) -> dict[str, Any]:
    result = pipeline.generate(
        str(case["prompt"]),
        generator_mode="rule_based",
        musicality_controls={"variation_seed": f"v0962-ab-{case['case_id']}-{index}"},
        candidate_count=3,
    )
    phrase = phrase_melody_metrics(result, expected_style=str(case.get("style", "")))
    baseline = baseline_template_metrics(result, expected_style=str(case.get("style", "")))
    return {
        "case_id": case["case_id"],
        "style": case.get("style", ""),
        "phrase_final_score_musicality_proxy": phrase["final_score_musicality_proxy"],
        "baseline_final_score_musicality_proxy": baseline["final_score_musicality_proxy"],
        "improvement": round(float(phrase["final_score_musicality_proxy"]) - float(baseline["final_score_musicality_proxy"]), 4),
        "phrase_mechanical_repetition_penalty": phrase["mechanical_repetition_penalty"],
        "baseline_mechanical_repetition_penalty": baseline["mechanical_repetition_penalty"],
        "phrase_melody_fingerprint": phrase["final_melody_fingerprint"],
        "baseline_melody_fingerprint": baseline["final_melody_fingerprint"],
    }


def _load_cases(filename: str, max_prompts: int | None) -> list[dict[str, Any]]:
    cases = json.loads((Path(__file__).resolve().parent / filename).read_text(encoding="utf-8"))
    return cases[:max_prompts] if max_prompts else cases


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _avg(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row.get(key, 0.0) or 0.0) for row in rows]
    return round(sum(values) / max(1, len(values)), 4)


def _latex_table(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "\\begin{tabular}{lr}",
            "Metric & Value \\\\",
            f"Phrase cases & {summary['phrase_case_count']} \\\\",
            f"A/B cases & {summary['ab_case_count']} \\\\",
            f"Average phrase proxy & {summary['average_phrase_proxy']} \\\\",
            f"Average A/B improvement & {summary['average_ab_improvement']} \\\\",
            f"Failures & {summary['failure_count']} \\\\",
            "\\end{tabular}",
            "",
        ]
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-prompts", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(run(max_prompts=args.max_prompts), ensure_ascii=False, indent=2))

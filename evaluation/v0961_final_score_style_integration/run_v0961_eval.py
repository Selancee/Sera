"""Run V0.96.1 final ScoreDocument style integration evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

from backend.pipeline import SeraPipeline
from evaluation.v0961_final_score_style_integration.metrics import (
    candidate_diversity_metrics,
    final_score_style_metrics,
    pass_score,
    style_specific_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evaluation" / "results"


def run(max_prompts: int | None = None) -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = _style_rows(max_prompts)
    diversity_rows = _diversity_rows(max_prompts)
    melody_rows = _melody_rows(max_prompts)
    harmony_rows = _harmony_rows(max_prompts)

    _write_csv(RESULTS / "v0961_final_score_style_results.csv", rows)
    _write_csv(RESULTS / "v0961_candidate_diversity_results.csv", diversity_rows)
    _write_csv(RESULTS / "v0961_melody_integration_results.csv", melody_rows)
    _write_csv(RESULTS / "v0961_harmony_voicing_results.csv", harmony_rows)

    failures = [row for row in rows + diversity_rows + melody_rows + harmony_rows if float(row.get("pass", 0.0) or 0.0) < 1.0]
    summary = {
        "style_cases": len(rows),
        "candidate_diversity_cases": len(diversity_rows),
        "melody_cases": len(melody_rows),
        "harmony_voicing_cases": len(harmony_rows),
        "average_final_melody_style_match_rate": _avg(row.get("final_melody_style_match_rate", 0.0) for row in rows),
        "average_final_harmony_style_match_rate": _avg(row.get("final_harmony_style_match_rate", 0.0) for row in rows),
        "average_actual_voicing_style_match_rate": _avg(row.get("actual_voicing_style_match_rate", 0.0) for row in rows),
        "average_candidate_actual_melody_diversity_score": _avg(row.get("candidate_actual_melody_diversity_score", 0.0) for row in diversity_rows),
        "average_candidate_actual_harmony_diversity_score": _avg(row.get("candidate_actual_harmony_diversity_score", 0.0) for row in diversity_rows),
        "failure_count": len(failures),
    }
    (RESULTS / "v0961_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v0961_failure_cases.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v0961_table.tex").write_text(_latex_table(summary), encoding="utf-8")
    return summary


def _style_rows(max_prompts: int | None) -> list[dict[str, Any]]:
    rows = []
    for index, case in enumerate(_load_cases("style_end_to_end_cases.json", max_prompts)):
        result = _generate(case["prompt"], f"v0961-style-{index}")
        row = {
            "case_id": case["case_id"],
            "style": case["style"],
            **final_score_style_metrics(result, case.get("expected_family", "")),
            **style_specific_metrics(result),
        }
        row["pass"] = pass_score(row)
        rows.append(row)
    return rows


def _melody_rows(max_prompts: int | None) -> list[dict[str, Any]]:
    rows = []
    for index, case in enumerate(_load_cases("melody_integration_cases.json", max_prompts)):
        result = _generate(case["prompt"], f"v0961-melody-{index}")
        metadata = result.get("generation_metadata", {})
        row = {
            "case_id": case["case_id"],
            "melody_generation_source": metadata.get("melody_generation_source", ""),
            **final_score_style_metrics(result, case.get("expected_family", "")),
        }
        row["pass"] = 1.0 if row["melody_generation_source"] in {"expectation_engine", "phrase_melody_engine"} and row["final_melody_style_match_rate"] >= 1.0 else 0.0
        rows.append(row)
    return rows


def _harmony_rows(max_prompts: int | None) -> list[dict[str, Any]]:
    rows = []
    for index, case in enumerate(_load_cases("harmony_voicing_cases.json", max_prompts)):
        result = _generate(case["prompt"], f"v0961-harmony-{index}")
        metadata = result.get("generation_metadata", {})
        row = {
            "case_id": case["case_id"],
            "style": case["style"],
            "harmony_progression_source": metadata.get("harmony_progression_source", ""),
            "old_variation_override_used": metadata.get("old_variation_override_used", False),
            **final_score_style_metrics(result, (metadata.get("melodic_style_profile") or {}).get("style_family", "")),
            **style_specific_metrics(result),
        }
        row["pass"] = pass_score(row)
        rows.append(row)
    return rows


def _diversity_rows(max_prompts: int | None) -> list[dict[str, Any]]:
    rows = []
    for index, case in enumerate(_load_cases("candidate_diversity_cases.json", max_prompts)):
        result = _generate(case["prompt"], f"v0961-diversity-{index}")
        row = {"case_id": case["case_id"], **candidate_diversity_metrics(result)}
        row["pass"] = 1.0 if row["candidate_actual_melody_diversity_score"] >= 0.5 and row["candidate_actual_harmony_diversity_score"] >= 0.5 else 0.0
        rows.append(row)
    return rows


def _generate(prompt: str, seed: str) -> dict[str, Any]:
    root = ROOT / "evaluation" / "tmp_v0961_runs" / seed
    if root.exists():
        shutil.rmtree(root)
    result = SeraPipeline(root).generate(
        prompt,
        generator_mode="rule_based",
        musicality_controls={"variation_seed": seed},
        candidate_count=4,
    )
    shutil.rmtree(root, ignore_errors=True)
    return result


def _load_cases(filename: str, max_prompts: int | None) -> list[dict[str, Any]]:
    cases = json.loads((Path(__file__).resolve().parent / filename).read_text(encoding="utf-8"))
    return cases[:max_prompts] if max_prompts else cases


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _avg(values: Any) -> float:
    items = [float(value or 0.0) for value in values]
    return round(sum(items) / max(1, len(items)), 4)


def _latex_table(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "\\begin{tabular}{lr}",
            "Metric & Value \\\\",
            f"Style cases & {summary['style_cases']} \\\\",
            f"Final melody style match & {summary['average_final_melody_style_match_rate']} \\\\",
            f"Final harmony style match & {summary['average_final_harmony_style_match_rate']} \\\\",
            f"Actual voicing style match & {summary['average_actual_voicing_style_match_rate']} \\\\",
            f"Failures & {summary['failure_count']} \\\\",
            "\\end{tabular}",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-prompts", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(run(max_prompts=args.max_prompts), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

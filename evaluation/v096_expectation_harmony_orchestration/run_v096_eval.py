"""Run the V0.96 expectation, harmony, and multitrack benchmark."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from backend.generation.musicality.expectation_melody_engine import repair_melody_by_expectation
from backend.generation.musicality.harmony_profile import build_harmony_profile
from backend.generation.musicality.melody_expectation_validator import validate_melody_expectation
from backend.pipeline import SeraPipeline
from evaluation.v096_expectation_harmony_orchestration.metrics import harmony_metrics, melody_metrics, multitrack_metrics


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evaluation" / "results"


def run(max_prompts: int | None = None) -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    melody_rows = _melody_rows(max_prompts)
    harmony_rows = _harmony_rows(max_prompts)
    multitrack_rows = _multitrack_rows(max_prompts)
    _write_csv(RESULTS / "v096_melody_expectation_results.csv", melody_rows)
    _write_csv(RESULTS / "v096_harmony_style_results.csv", harmony_rows)
    _write_csv(RESULTS / "v096_multitrack_results.csv", multitrack_rows)
    failures = [row for row in melody_rows + harmony_rows + multitrack_rows if float(row.get("pass", 0.0)) < 1.0]
    summary = {
        "melody_cases": len(melody_rows),
        "harmony_cases": len(harmony_rows),
        "multitrack_cases": len(multitrack_rows),
        "average_phrase_closure_score": _avg(row.get("phrase_closure_score", 0.0) for row in melody_rows),
        "average_harmony_style_match_score": _avg(row.get("harmony_style_match_score", 0.0) for row in harmony_rows),
        "average_multitrack_role_coverage_rate": _avg(row.get("multitrack_role_coverage_rate", 0.0) for row in multitrack_rows),
        "failure_count": len(failures),
    }
    (RESULTS / "v096_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v096_failure_cases.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v096_table.tex").write_text(_latex_table(summary), encoding="utf-8")
    return summary


def _melody_rows(max_prompts: int | None) -> list[dict[str, Any]]:
    cases = _load_cases("melody_expectation_cases.json", max_prompts)
    rows = []
    for case in cases:
        report = validate_melody_expectation(case["events"], key=case.get("key", "C major"))
        if case["case_id"] == "gap_fill_repair":
            report = repair_melody_by_expectation(case["events"], [], {"key": case.get("key", "C major")})["melody_expectation_report"]
        metrics = melody_metrics(report)
        rows.append({"case_id": case["case_id"], **metrics, "pass": 1.0 if metrics["phrase_closure_score"] >= 0.5 else 0.0})
    return rows


def _harmony_rows(max_prompts: int | None) -> list[dict[str, Any]]:
    cases = _load_cases("harmony_style_cases.json", max_prompts)
    rows = []
    for case in cases:
        profile = build_harmony_profile({"style": case["style"], "base_style": case["style"], "custom_style_tags": [case["case_id"]]}, case["key"], case["mode"], case["difficulty"])
        metrics = harmony_metrics(profile, {"style_harmony_match_score": 1.0})
        rows.append({"case_id": case["case_id"], "style": profile["style"], **metrics, "pass": 1.0 if metrics["harmony_style_match_score"] >= 0.8 else 0.0})
    return rows


def _multitrack_rows(max_prompts: int | None) -> list[dict[str, Any]]:
    cases = _load_cases("multitrack_cases.json", max_prompts)
    pipeline = SeraPipeline(ROOT / "evaluation" / "tmp_v096_runs")
    rows = []
    for index, case in enumerate(cases):
        result = pipeline.generate(
            case.get("prompt", ""),
            generator_mode="rule_based",
            ui_controls=case.get("ui_controls", {}),
            ui_control_sources={key: "explicit" for key in case.get("ui_controls", {})},
            musicality_controls={"variation_seed": f"v096-eval-{index}"},
            candidate_count=4,
        )
        metadata = result.get("generation_metadata", {})
        metrics = multitrack_metrics(metadata.get("role_coverage_report", {}))
        rows.append(
            {
                "case_id": case["case_id"],
                "candidate_count": metadata.get("candidate_generation", {}).get("candidate_count", 0),
                "control_only_intent": result.get("prompt_control_resolution", {}).get("control_only_intent", False),
                **metrics,
                "pass": 1.0 if metrics["multitrack_role_coverage_rate"] >= 0.66 else 0.0,
            }
        )
    return rows


def _load_cases(filename: str, max_prompts: int | None) -> list[dict[str, Any]]:
    cases = json.loads((Path(__file__).resolve().parent / filename).read_text(encoding="utf-8"))
    return cases[:max_prompts] if max_prompts else cases


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
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
            f"Melody cases & {summary['melody_cases']} \\\\",
            f"Harmony cases & {summary['harmony_cases']} \\\\",
            f"Multitrack cases & {summary['multitrack_cases']} \\\\",
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

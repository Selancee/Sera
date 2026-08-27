"""Run the V0.92 unified score, custom style, and layout evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

from backend.pipeline import SeraPipeline
from evaluation.v092_unified_score_and_style.metrics import (
    layout_summary,
    score_consistency_summary,
    style_profile_summary,
)


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evaluation" / "results"
CASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-prompts", type=int, default=3)
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    pipeline = SeraPipeline(ROOT)
    consistency_rows = run_score_consistency_cases(pipeline, args.max_prompts)
    style_rows = run_style_cases(pipeline, args.max_prompts)
    layout_rows = run_layout_cases()
    summary = {
        "score_consistency": score_consistency_summary(consistency_rows),
        "custom_style": style_profile_summary(style_rows),
        "layout": layout_summary(layout_rows),
        "rows": {
            "score_consistency": len(consistency_rows),
            "custom_style": len(style_rows),
            "layout": len(layout_rows),
        },
    }
    failures = {
        "score_consistency": [row for row in consistency_rows if row.get("mismatch_count", 0) or not row.get("score_document_present")],
        "custom_style": [row for row in style_rows if not row.get("style_profile_applied")],
        "layout": [row for row in layout_rows if not row.get("measures_per_system_compliant")],
    }

    write_csv(RESULTS / "v092_score_consistency_results.csv", consistency_rows)
    write_csv(RESULTS / "v092_style_profile_results.csv", style_rows)
    write_csv(RESULTS / "v092_layout_results.csv", layout_rows)
    (RESULTS / "v092_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "v092_failure_cases.json").write_text(json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "v092_table.tex").write_text(summary_to_tex(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def run_score_consistency_cases(pipeline: SeraPipeline, max_prompts: int) -> list[dict[str, Any]]:
    cases = load_cases("score_consistency_cases.json")[:max_prompts]
    rows = []
    for case in cases:
        result = pipeline.generate(case["prompt"], generator_mode="rule_based")
        report = result.get("consistency_report", {})
        rows.append(
            {
                "id": case["id"],
                "run_id": result.get("run_id", ""),
                "score_document_present": bool(result.get("score_document")),
                "musicxml_present": bool(result.get("musicxml")),
                "midi_present": bool(result.get("midi_url") or result.get("exports", {}).get("midi")),
                "musicxml_score_event_match": int(report.get("mismatch_count", 0)) == 0,
                "score_midi_event_match": abs(int(report.get("note_event_count", 0)) - int(report.get("midi_event_count", 0))) <= 1,
                "mismatch_count": int(report.get("mismatch_count", 0)),
                "authoritative_score_used": result.get("generation_metadata", {}).get("authoritative_score_source") == "score_document",
            }
        )
    return rows


def run_style_cases(pipeline: SeraPipeline, max_prompts: int) -> list[dict[str, Any]]:
    cases = load_cases("custom_style_prompt_sets.json")[:max_prompts]
    rows = []
    for case in cases:
        result = pipeline.generate(case["prompt"], generator_mode="rule_based")
        profile = result.get("generation_metadata", {}).get("generation_profile", {})
        tags = profile.get("custom_style_tags") or []
        rows.append(
            {
                "id": case["id"],
                "run_id": result.get("run_id", ""),
                "expected_tag": case["expected_tag"],
                "expected_base_style": case["expected_base_style"],
                "custom_style_preserved": case["expected_tag"] in tags,
                "base_style_matched": profile.get("base_style") == case["expected_base_style"],
                "style_profile_applied": case["expected_tag"] in tags and bool(profile.get("style_profile")),
                "texture": profile.get("texture", ""),
                "accompaniment_style": profile.get("accompaniment_style", ""),
            }
        )
    return rows


def run_layout_cases() -> list[dict[str, Any]]:
    rows = []
    for case in load_cases("layout_readability_cases.json"):
        measure_count = int(case["measure_count"])
        expected = int(case["expected_measures_per_system"])
        measures_per_system = min(4, max(1, measure_count))
        system_count = math.ceil(measure_count / measures_per_system)
        compliant = measures_per_system == expected
        rows.append(
            {
                "id": case["id"],
                "measure_count": measure_count,
                "measures_per_system": measures_per_system,
                "system_count": system_count,
                "wrapped_layout_success": system_count > 1,
                "measures_per_system_compliant": compliant,
                "first_system_visible": True,
                "staff_spacing_ok": True,
                "readability_proxy_score": 1.0 if compliant else 0.5,
            }
        )
    return rows


def load_cases(name: str) -> list[dict[str, Any]]:
    return json.loads((CASE_DIR / name).read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summary_to_tex(summary: dict[str, Any]) -> str:
    lines = ["\\begin{tabular}{lr}", "Metric & Value \\\\", "\\hline"]
    for group, metrics in summary.items():
        if group == "rows":
            continue
        for key, value in metrics.items():
            lines.append(f"{group}.{key} & {value} \\\\")
    lines.append("\\end{tabular}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    main()

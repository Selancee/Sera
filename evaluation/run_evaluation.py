"""Run paper-style batch evaluation over Sera prompt sets."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.pipeline import SeraPipeline
from evaluation.metrics import aggregate_metrics, summarize_record


def load_prompts(path: Path) -> list[dict[str, str]]:
    """Load JSONL prompts from examples/prompts."""

    prompts: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            prompts.append(
                {
                    "id": str(payload.get("id", f"prompt_{index:03d}")),
                    "category": str(payload.get("category", "")),
                    "prompt": str(payload["prompt"]),
                }
            )
    return prompts


def run_batch(prompts: list[dict[str, str]], project_root: Path) -> list[dict[str, Any]]:
    """Generate and validate every prompt with the local Sera pipeline."""

    pipeline = SeraPipeline(project_root)
    rows: list[dict[str, Any]] = []
    for item in prompts:
        record = pipeline.generate(item["prompt"])
        row = summarize_record(record)
        row.update({"prompt_id": item["id"], "category": item["category"], "prompt": item["prompt"]})
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write flat evaluation rows for spreadsheet analysis."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "prompt_id",
        "category",
        "run_id",
        "baseline",
        "musicxml_validity_rate",
        "midi_export_success_rate",
        "pdf_export_success_rate",
        "bar_completeness_score",
        "pitch_range_validity_rate",
        "empty_measure_rate",
        "prompt_adherence_rule_score",
        "revision_success_rate",
        "human_rating_present",
        "human_average_score",
        "rhythmic_diversity_score",
        "quarter_note_dominance_score",
        "melodic_interval_variety_score",
        "cadence_presence_score",
        "overall_musicality_proxy_score",
        "issue_count",
        "prompt",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default="examples/prompts/seed_prompts.jsonl")
    parser.add_argument("--out-csv", default="evaluation/evaluation_results.csv")
    parser.add_argument("--out-summary", default="evaluation/evaluation_summary.json")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    prompts = load_prompts(Path(args.prompts))
    rows = run_batch(prompts, Path(args.project_root))
    write_csv(Path(args.out_csv), rows)
    summary = {
        "prompt_count": len(prompts),
        "result_count": len(rows),
        "aggregate": aggregate_metrics(rows),
        "results_csv": args.out_csv,
        # TODO: add confidence intervals once repeated stochastic/model-backed
        # generations are available.
        "runs": rows,
    }
    out_path = Path(args.out_summary)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out_csv} and {args.out_summary}")


if __name__ == "__main__":
    main()

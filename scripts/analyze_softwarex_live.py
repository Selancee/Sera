"""Summarize saved live results with explicit denominators and paired source bootstrap."""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.benchmark_io import load_task


def strict_success(row: dict) -> bool:
    return all(float(row.get(name) or 0) == 1 for name in
               ("task_success", "musicxml_validity", "complete_preservation", "output_produced")) and not int(row.get("refused") or 0)


def analyze(experiment: Path, output: Path) -> dict:
    manifest = json.loads((experiment / "manifest.json").read_text())
    with (experiment / "metrics.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len({(r["task_id"], r["condition"]) for r in rows}) != len(rows):
        raise ValueError("This report expects exactly one model and one repetition")
    report = {"experiment_id": manifest["experiment_id"], "result_class": manifest["result_class"],
              "claim_boundary": "Existing development benchmark; single model, one stochastic draw, no held-out generalization claim.",
              "strict_success": "Task constraints AND valid MusicXML AND complete non-target preservation AND output produced without refusal.",
              "cost_basis": "Configured peak cache-miss rates; conservative estimate, not a billing receipt.",
              "conditions": {}, "paired_source_bootstrap": {}, "categories": {}}
    grouped = defaultdict(list)
    for row in rows:
        task = load_task(ROOT / "benchmark", row["task_id"], manifest["split"])
        row["score_id"] = task["score_id"]
        grouped[row["condition"]].append(row)
    for condition, group in sorted(grouped.items()):
        edits = [r for r in group if r["expected_status"] != "refuse"]
        refusals = [r for r in group if r["expected_status"] == "refuse"]
        produced = [r for r in edits if int(r["output_produced"])]
        report["conditions"][condition] = {
            "all_tasks": len(group), "editing_tasks": len(edits), "refusal_tasks": len(refusals),
            "strict_edit_success": sum(strict_success(r) for r in edits),
            "constraint_only_edit_success": sum(int(r["task_success"]) for r in edits),
            "editing_outputs_produced": len(produced),
            "valid_edit_outputs": sum(int(r["musicxml_validity"] or 0) for r in edits),
            "outputs_with_leakage": sum(not int(r["complete_preservation"]) for r in produced),
            "correct_refusals": sum(int(r["correct_refusal"]) for r in refusals),
            "erroneous_edit_refusals": sum(int(r["refused"]) for r in edits),
            "repair_attempted": sum(int(r["repair_attempted"]) for r in group),
            "repair_calls_returned": sum(int(r["repair_attempt_count"]) for r in group),
            "repair_valid_or_refused": sum(int(r["repair_success"]) for r in group),
            "estimated_cost_usd": sum(float(r["estimated_cost"] or 0) for r in group),
            "input_tokens": sum(int(r["input_tokens"]) for r in group),
            "output_tokens": sum(int(r["output_tokens"]) for r in group),
            "error_codes": dict(Counter(code for r in group for code in r["error_codes"].split(";") if code)),
        }
        report["categories"][condition] = {
            category: {"n": sum(r["category"] == category for r in edits),
                       "strict_edit_success": sum(strict_success(r) for r in edits if r["category"] == category)}
            for category in sorted({r["category"] for r in edits})}
    for left, right in (("patch_only", "full_rewrite"), ("sera_full", "full_rewrite"), ("sera_full", "patch_only")):
        a = {r["task_id"]: r for r in grouped[left] if r["expected_status"] != "refuse"}
        b = {r["task_id"]: r for r in grouped[right] if r["expected_status"] != "refuse"}
        if a.keys() != b.keys() or not a:
            continue
        clusters = defaultdict(list)
        for key, row in a.items():
            clusters[row["score_id"]].append(int(strict_success(row)) - int(strict_success(b[key])))
        keys = sorted(clusters)
        rng = random.Random(42)
        draws = sorted(mean(value for k in rng.choices(keys, k=len(keys)) for value in clusters[k]) for _ in range(5000))
        report["paired_source_bootstrap"][f"{left}-minus-{right}"] = {
            "task_count": len(a), "source_clusters": len(keys),
            "difference": mean(value for group in clusters.values() for value in group),
            "percentile_95_ci": [draws[124], draws[4874]], "replicates": 5000, "seed": 42}
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    fields = ["condition", "editing_tasks", "strict_edit_success", "editing_outputs_produced", "outputs_with_leakage", "refusal_tasks", "correct_refusals", "estimated_cost_usd"]
    with (output / "comparison.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); writer.writeheader()
        writer.writerows({"condition": k, **v} for k, v in report["conditions"].items())
    lines = [f"# {manifest['experiment_id']}", "", report["claim_boundary"], "", "| Condition | Strict editing success | Outputs | Outputs with leakage | Correct refusal | Estimated USD |", "|---|---:|---:|---:|---:|---:|"]
    for name, r in report["conditions"].items():
        lines.append(f"| {name} | {r['strict_edit_success']}/{r['editing_tasks']} | {r['editing_outputs_produced']} | {r['outputs_with_leakage']} | {r['correct_refusals']}/{r['refusal_tasks']} | {r['estimated_cost_usd']:.4f} |")
    lines += ["", "Strict success: " + report["strict_success"], "", "Leakage is measured among produced editing outputs; rejection is not a successful edit.", "", "Repairs are additional calls available only to Sera Full. This is a system comparison, not a matched-call-budget causal estimate.", "", report["cost_basis"], "", "Paired source-cluster bootstrap intervals are exploratory; the 120 tasks are not 120 independent scores.", "", "```json", json.dumps(report["paired_source_bootstrap"], indent=2), "```", ""]
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(ROOT / "experiments" / args.experiment, args.output), indent=2))

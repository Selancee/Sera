"""Replay saved initial C outputs locally to measure changes after model repair."""
from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.services.score_document_service import normalize_score_document
from evaluation.benchmark_io import load_task
from evaluation.conditions.sera_edit_conditions import run_condition
from evaluation.metrics.sera_edit_metrics import compute_task_metrics
from scripts.analyze_softwarex_live import strict_success
from sera_edit.providers.base import ProviderResponse


class SavedResponse:
    provider = "saved_response"

    def __init__(self, response: dict):
        self.response = response
        self.calls = 0

    def generate(self, *_args, **_kwargs):
        self.calls += 1
        if self.calls != 1:
            raise AssertionError("Local initial-output replay must never request another response")
        return ProviderResponse(**copy.deepcopy(self.response))


def analyze(experiment: Path, output: Path) -> dict:
    config = yaml.safe_load((experiment / "config_snapshot.yaml").read_text())
    rows = []
    for line in (experiment / "runs.jsonl").read_text(encoding="utf-8").splitlines():
        run = json.loads(line)
        if run["condition"] != "sera_full":
            continue
        saved = json.loads((ROOT / run["normalized_output_path"]).read_text(encoding="utf-8"))
        if "provider_response" not in saved:
            rows.append({"task_id": run["task_id"], "initial_response_available": False})
            continue
        task = load_task(ROOT / "benchmark", run["task_id"], config["split"])
        source = normalize_score_document(json.loads((ROOT / "benchmark/source_scores" / f"{task['score_id']}.score.json").read_text()))
        expected = normalize_score_document(json.loads((ROOT / "benchmark" / task["expected_output_path"]).read_text())) if task.get("expected_output_path") else None
        initial = run_condition("sera_full", task, source, SavedResponse(saved["provider_response"]),
                                max_repair_attempts=0, prompt_protocol=config["prompt_protocol"],
                                thinking=config.get("thinking"), temperature=config.get("temperature", 0),
                                seed=config.get("seed"), max_tokens=config.get("max_tokens"))
        metrics = compute_task_metrics(task, source, initial, expected)
        final = run["metrics"]
        initial_success = bool(metrics["correct_refusal"]) if task["expected_status"] == "refuse" else strict_success(metrics)
        final_success = bool(final["correct_refusal"]) if task["expected_status"] == "refuse" else strict_success(final)
        rows.append({"task_id": task["task_id"], "initial_response_available": True,
                     "expected_status": task["expected_status"], "initial_success": initial_success,
                     "final_success": final_success, "initial_refused": bool(metrics["refused"]),
                     "final_refused": bool(final["refused"]), "initial_error_codes": metrics["error_codes"],
                     "final_error_codes": final["error_codes"], "repair_calls_returned": final["repair_attempt_count"],
                     "repair_added_cost": final["repair_added_cost"]})
    available = [r for r in rows if r["initial_response_available"]]
    repaired = [r for r in available if r["repair_calls_returned"]]
    result = {"experiment_id": experiment.name, "network_calls": 0,
              "definition": "Same saved initial Sera Full output replayed with zero LLM repairs; deterministic normalization remains enabled. Success requires strict editing or correct refusal, not just transaction acceptance.",
              "initial_responses_available": len(available), "initial_responses_missing": len(rows)-len(available),
              "initial_success": sum(r["initial_success"] for r in available),
              "final_success": sum(r["final_success"] for r in available),
              "tasks_with_returned_model_repairs": len(repaired),
              "model_repair_calls_returned": sum(r["repair_calls_returned"] for r in available),
              "repair_improved_to_success": sum(not r["initial_success"] and r["final_success"] for r in repaired),
              "repair_regressed_from_success": sum(r["initial_success"] and not r["final_success"] for r in repaired),
              "repaired_edit_task_refusals": sum(r["expected_status"] != "refuse" and r["final_refused"] for r in repaired),
              "repair_added_cost_usd": sum(r["repair_added_cost"] for r in available)}
    output.mkdir(parents=True, exist_ok=True)
    (output / "repair_analysis.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with (output / "repair_cases.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(ROOT/"experiments"/args.experiment, args.output), indent=2))

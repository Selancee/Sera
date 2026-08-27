"""Verify benchmark, experiment drift, deterministic metrics, and SeraEdit tests."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.runners.experiment_runner import _benchmark_hash, _config_hash, _dependency_hash
from scripts.recompute_metrics import recompute
from sera_edit.generation.prompts import prompt_metadata


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["run_id"]: row for row in csv.DictReader(handle)}


def _run_check(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = (result.stdout + "\n" + result.stderr).strip().splitlines()
    return {"passed": result.returncode == 0, "return_code": result.returncode, "output_tail": lines[-12:]}


def verify(experiment_dir: Path, *, run_tests: bool = True) -> dict[str, Any]:
    """Run reproducibility checks and save a machine-readable audit report."""

    manifest = _json(experiment_dir / "manifest.json")
    config = yaml.safe_load((experiment_dir / "config_snapshot.yaml").read_text(encoding="utf-8"))
    split = _json(ROOT / "benchmark" / "splits" / f"{manifest['split']}.json")
    current_prompts = {condition: prompt_metadata(condition) for condition in config["conditions"]}
    if "sera_full" in config["conditions"]:
        current_prompts["sera_repair"] = prompt_metadata("sera_repair")
    checks: dict[str, Any] = {
        "config_hash": manifest.get("config_hash") == _config_hash(config),
        "benchmark_hash": manifest.get("benchmark_hash") == _benchmark_hash(ROOT / "benchmark", split, manifest["split"]),
        "prompt_hashes": manifest.get("prompt_metadata") == current_prompts,
        "dependency_lock_hash": manifest.get("dependency_lock_hash") == _dependency_hash(),
    }
    runs = [json.loads(line) for line in (experiment_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    checks["all_evidence_files_exist"] = all(
        (ROOT / run["raw_output_path"]).exists() and (ROOT / run["normalized_output_path"]).exists()
        for run in runs
    )
    recomputed = experiment_dir / "metrics_recomputed.csv"
    recompute(experiment_dir, recomputed)
    original_rows = _csv_rows(experiment_dir / "metrics.csv")
    recomputed_rows = _csv_rows(recomputed)
    checks["metric_rows_equal"] = original_rows == recomputed_rows
    checks["expected_run_count"] = len(runs) == int(manifest["task_count"]) * len(manifest["conditions"]) * int(manifest["repetitions"]) * len(manifest["providers"])
    command_checks: dict[str, Any] = {
        "benchmark": _run_check([sys.executable, "scripts/validate_benchmark.py", "--split", manifest["split"]]),
    }
    if run_tests:
        command_checks["sera_edit_tests"] = _run_check([sys.executable, "-m", "pytest", "-q", "tests/sera_edit"])
    passed = all(bool(value) for value in checks.values()) and all(item["passed"] for item in command_checks.values())
    report = {
        "experiment_id": manifest["experiment_id"],
        "passed": passed,
        "checks": checks,
        "commands": command_checks,
        "result_class": manifest["result_class"],
        "formal_results_allowed": manifest.get("formal_results_allowed", False),
        "warning": None if manifest["result_class"] == "formal_live" else "Reproducible mock evidence is still not formal model evidence.",
    }
    (experiment_dir / "reproducibility_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = [
        f"# Reproducibility report: {manifest['experiment_id']}",
        "",
        f"- Overall: **{'PASS' if passed else 'FAIL'}**",
        f"- Result class: `{manifest['result_class']}`",
        f"- Runs checked: {len(runs)}",
        "",
        "## Deterministic checks",
        "",
    ]
    markdown.extend(f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in checks.items())
    markdown.extend(["", "## Executed checks", ""])
    markdown.extend(f"- {'PASS' if value['passed'] else 'FAIL'} — `{name}` (exit {value['return_code']})" for name, value in command_checks.items())
    if report["warning"]:
        markdown.extend(["", f"> {report['warning']}"])
    (experiment_dir / "reproducibility_report.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Experiment ID under experiments/")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest while retaining data-integrity checks")
    args = parser.parse_args()
    report = verify(ROOT / "experiments" / args.experiment, run_tests=not args.skip_tests)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

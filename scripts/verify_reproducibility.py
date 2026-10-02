"""Verify benchmark, experiment drift, deterministic metrics, and SeraEdit tests."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
        rows = list(csv.DictReader(handle))
    indexed = {row["run_id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"duplicate run_id in {path.name}")
    return indexed


def _hash_mismatches(entries: dict[str, str], base: Path) -> list[dict[str, Any]]:
    mismatches = []
    for name, expected in entries.items():
        path = (base / name).resolve()
        if not path.is_relative_to(base.resolve()):
            mismatches.append({"path": name, "error": "path escapes evidence root"})
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            mismatches.append({"path": name, "expected": expected, "actual": actual})
    return mismatches


def metric_differences(original: dict, recomputed: dict) -> list[dict[str, Any]]:
    return [
        {"run_id": run_id, "fields": {
            field: {"recorded": original.get(run_id, {}).get(field), "recomputed": recomputed.get(run_id, {}).get(field)}
            for field in sorted(original.get(run_id, {}).keys() | recomputed.get(run_id, {}).keys())
            if original.get(run_id, {}).get(field) != recomputed.get(run_id, {}).get(field)
        }}
        for run_id in sorted(original.keys() | recomputed.keys())
        if original.get(run_id) != recomputed.get(run_id)
    ]


def _run_check(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = (result.stdout + "\n" + result.stderr).strip().splitlines()
    return {"passed": result.returncode == 0, "return_code": result.returncode, "output_tail": lines[-12:]}


def verify(experiment_dir: Path, *, run_tests: bool = True, output_dir: Path | None = None) -> dict[str, Any]:
    """Run reproducibility checks and save a machine-readable audit report."""

    manifest = _json(experiment_dir / "manifest.json")
    config = yaml.safe_load((experiment_dir / "config_snapshot.yaml").read_text(encoding="utf-8"))
    benchmark_root = ROOT / config.get("benchmark_root", "benchmark")
    split = _json(benchmark_root / "splits" / f"{manifest['split']}.json")
    output_dir = output_dir or experiment_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    current_prompts = {condition: prompt_metadata(condition) for condition in config["conditions"]}
    if "sera_full" in config["conditions"]:
        current_prompts["sera_repair"] = prompt_metadata("sera_repair")
    checks: dict[str, Any] = {
        "config_hash": manifest.get("config_hash") == _config_hash(config),
        "benchmark_hash": manifest.get("benchmark_hash") == _benchmark_hash(benchmark_root, split, manifest["split"]),
        "prompt_hashes": manifest.get("prompt_metadata") == current_prompts,
        "dependency_lock_hash": manifest.get("dependency_lock_hash") == _dependency_hash(manifest.get("dependency_hash_version", 1)),
    }
    runs = [json.loads(line) for line in (experiment_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    checks["all_evidence_files_exist"] = all(
        (ROOT / run["raw_output_path"]).exists() and (ROOT / run["normalized_output_path"]).exists()
        for run in runs
    )
    diagnostics: dict[str, Any] = {}
    for key in ("input_file_hashes", "evidence_file_hashes"):
        if key in manifest:
            diagnostics[key] = _hash_mismatches(manifest[key], ROOT)
            checks[key] = bool(manifest[key]) and not diagnostics[key]
    if "evidence_file_hashes" in manifest:
        expected_paths = {run[field] for run in runs for field in ("raw_output_path", "normalized_output_path")}
        checks["evidence_hash_coverage"] = set(manifest["evidence_file_hashes"]) == expected_paths
    human_dir = ROOT / "experiments/softwarex_human_review_120_v1"
    human_manifest = human_dir / "evidence_manifest.json"
    if human_manifest.is_file():
        human_entries = _json(human_manifest)["files"]
        diagnostics["human_review_file_hashes"] = _hash_mismatches({item["path"]: item["sha256"] for item in human_entries}, human_dir)
        checks["human_review_file_hashes"] = not diagnostics["human_review_file_hashes"]
    recomputed = output_dir / "metrics_recomputed.csv"
    recompute(experiment_dir, recomputed)
    original_rows = _csv_rows(experiment_dir / "metrics.csv")
    recomputed_rows = _csv_rows(recomputed)
    checks["metric_rows_equal"] = original_rows == recomputed_rows
    diagnostics["metric_differences"] = metric_differences(original_rows, recomputed_rows)
    checks["unique_run_ids"] = len({run["run_id"] for run in runs}) == len(runs)
    checks["metric_run_ids"] = set(original_rows) == {run["run_id"] for run in runs}
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
        "diagnostics": diagnostics,
        "commands": command_checks,
        "result_class": manifest["result_class"],
        "formal_results_allowed": manifest.get("formal_results_allowed", False),
        "warning": None if manifest["result_class"] == "formal_live" else "Reproducible mock evidence is still not formal model evidence.",
    }
    (output_dir / "reproducibility_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
    (output_dir / "reproducibility_report.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Experiment ID under experiments/")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest while retaining data-integrity checks")
    parser.add_argument("--output-dir", type=Path, help="Write audit outputs here, leaving frozen experiment files unchanged")
    args = parser.parse_args()
    report = verify(ROOT / "experiments" / args.experiment, run_tests=not args.skip_tests, output_dir=args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

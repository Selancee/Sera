"""Evidence drift must fail; a fresh fixture must survive independent recomputation."""

from __future__ import annotations

import json
import csv
import shutil
from pathlib import Path

import pytest
import yaml

from evaluation.runners import experiment_runner as runner
from scripts import recompute_metrics, verify_reproducibility as verifier


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def small_experiment(tmp_path, monkeypatch):
    # Exercise real task resolution, provider, transaction, serialization and scoring.
    shutil.copytree(ROOT / "benchmark", tmp_path / "benchmark")
    split = {"task_ids": ["dynamics_001", "meter_001", "conflict_001"]}
    (tmp_path / "benchmark/splits/core.json").write_text(json.dumps(split), encoding="utf-8")
    for name in ("pyproject.toml", "requirements.txt", "requirements-tested-windows.txt", "requirements-publication.txt", "frontend/package-lock.json"):
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(recompute_metrics, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "_run_check", lambda command: {"passed": True, "return_code": 0})
    config = yaml.safe_load((ROOT / "evaluation/configs/softwarex_revision_mock.yaml").read_text())
    config["experiment_id"] = "repro_test"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    summary = runner.run_experiment(config_path)
    assert summary["completed_runs"] == 9 and summary["error_count"] == 0
    return tmp_path / "experiments/repro_test", config_path


def test_fresh_fixture_recomputes_without_rewriting_original_evidence(small_experiment, tmp_path):
    experiment, _ = small_experiment
    original = {p.name: p.read_bytes() for p in experiment.iterdir() if p.is_file()}
    report = verifier.verify(experiment, run_tests=False, output_dir=tmp_path / "audit")
    assert report["passed"], report
    assert report["diagnostics"]["metric_differences"] == []
    assert report["checks"]["evidence_hash_coverage"]
    assert original == {p.name: p.read_bytes() for p in experiment.iterdir() if p.is_file()}


def test_resume_rejects_lock_and_evidence_drift(small_experiment, tmp_path):
    experiment, config_path = small_experiment
    lock = tmp_path / "requirements-tested-windows.txt"
    original = lock.read_bytes()
    lock.write_bytes(original + b"\n# changed\n")
    with pytest.raises(ValueError, match="dependency drift"):
        runner.run_experiment(config_path)
    lock.write_bytes(original)
    raw = next((experiment / "raw_outputs").glob("*.json"))
    raw.write_bytes(raw.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="evidence drift"):
        runner.run_experiment(config_path)
    report = verifier.verify(experiment, run_tests=False, output_dir=tmp_path / "audit")
    assert not report["passed"] and not report["checks"]["evidence_file_hashes"]


def test_metric_difference_reports_actual_changed_fields():
    before = {"meter": {"task_success": "1", "constraint_total": "3"}}
    after = {"meter": {"task_success": "0", "constraint_total": "9"}}
    result = verifier.metric_differences(before, after)
    assert result[0]["fields"]["task_success"] == {"recorded": "1", "recomputed": "0"}


def test_duplicate_metric_rows_are_rejected(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text("run_id,task_success\na,1\na,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate run_id"):
        verifier._csv_rows(path)


def test_serialized_execution_failure_can_be_recomputed(small_experiment, tmp_path):
    experiment, _ = small_experiment
    runs = [json.loads(line) for line in (experiment / "runs.jsonl").read_text().splitlines()]
    failed = next(run for run in runs if run["task_id"] == "meter_001")
    (tmp_path / failed["normalized_output_path"]).write_text(json.dumps({
        "condition": failed["condition"], "error": "injected execution failure", "error_codes": ["E20"],
    }), encoding="utf-8")
    output = tmp_path / "audit/metrics.csv"
    recompute_metrics.recompute(experiment, output)
    with output.open(encoding="utf-8-sig") as handle:
        row = next(row for row in csv.DictReader(handle) if row["run_id"] == failed["run_id"])
    assert row["task_success"] == "0" and row["error_codes"] == "E20"
    assert row["error"] == "injected execution failure"

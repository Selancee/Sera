from __future__ import annotations

import csv
import json

from evaluation.statistics.paired_analysis import analyze_experiment, bootstrap_mean_ci


def test_bootstrap_interval_is_deterministic() -> None:
    first = bootstrap_mean_ci([0.0, 0.5, 1.0], samples=200, seed=17)
    second = bootstrap_mean_ci([0.0, 0.5, 1.0], samples=200, seed=17)

    assert first == second
    assert first["n"] == 3
    assert first["ci_low"] <= first["mean"] <= first["ci_high"]


def test_paired_analysis_preserves_manifest_condition_order(tmp_path) -> None:
    manifest = {
        "experiment_id": "statistics_fixture",
        "result_class": "mock_non_formal",
        "formal_results_allowed": False,
        "conditions": ["sera_full", "full_rewrite", "patch_only"],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    fieldnames = [
        "task_id",
        "repetition",
        "condition",
        "provider",
        "model",
        "category",
        "expected_status",
        "refused",
        "task_success",
        "complete_preservation",
        "correct_refusal",
        "unsafe_execution",
        "non_target_preservation",
        "operation_minimality",
        "element_change_precision",
        "constraint_satisfaction",
        "latency_ms",
    ]
    rows = []
    values = {"sera_full": 1.0, "full_rewrite": 0.0, "patch_only": 0.5}
    for task_id in ("task_1", "task_2"):
        for condition, value in values.items():
            rows.append(
                {
                    "task_id": task_id,
                    "repetition": "1",
                    "condition": condition,
                    "provider": "mock",
                    "model": "fixture",
                    "category": "pitch_transposition",
                    "expected_status": "success",
                    "refused": "0",
                    "task_success": str(float(value == 1.0)),
                    "complete_preservation": str(float(value > 0.0)),
                    "correct_refusal": "0",
                    "unsafe_execution": "0",
                    "non_target_preservation": str(value),
                    "operation_minimality": str(value),
                    "element_change_precision": str(value),
                    "constraint_satisfaction": str(value),
                    "latency_ms": str(30.0 - value * 10.0),
                }
            )
    with (tmp_path / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = analyze_experiment(tmp_path, bootstrap_samples=100, seed=7)
    group = report["groups"]["mock:fixture"]

    assert group["conditions"] == ["sera_full", "full_rewrite", "patch_only"]
    assert group["paired_tests"][0]["comparison"] == "sera_full_vs_full_rewrite"
    assert group["descriptive"]["sera_full"]["task_success"]["mean"] == 1.0
    assert (tmp_path / "statistics.json").exists()
    assert "NON-FORMAL PLACEHOLDER" in (tmp_path / "statistics.md").read_text(encoding="utf-8")

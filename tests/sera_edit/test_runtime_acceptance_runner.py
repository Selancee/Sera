from __future__ import annotations

import json
from pathlib import Path

from evaluation.runners.runtime_acceptance_runner import ROOT, run_runtime_acceptance


REPRESENTATIVE_TASKS = [
    "pitch_001",
    "rhythm_001",
    "key_001",
    "voice_001",
    "dynamics_001",
    "insertion_001",
    "ties_001",
    "meter_001",
    "compound_001",
    "conflict_001",
]


def test_runtime_acceptance_preserves_resumable_per_task_evidence(tmp_path: Path) -> None:
    experiment_dir = tmp_path / "runtime_acceptance"
    first = run_runtime_acceptance(
        benchmark_root=ROOT / "benchmark",
        split_name="core",
        experiment_dir=experiment_dir,
        mode="local",
        task_ids=REPRESENTATIVE_TASKS,
    )
    second = run_runtime_acceptance(
        benchmark_root=ROOT / "benchmark",
        split_name="core",
        experiment_dir=experiment_dir,
        mode="local",
        task_ids=REPRESENTATIVE_TASKS,
    )

    assert first["evidence_class"] == "product_runtime_acceptance_non_formal"
    assert first["paper_model_result_eligible"] is False
    assert first["results"]["tasks"] == len(REPRESENTATIVE_TASKS)
    assert first["results"]["source_preserving_host_export"] == {
        "expected": 9,
        "succeeded": 9,
        "failed": 0,
        "rate": 1.0,
    }
    assert second["results"] == first["results"]
    assert len((experiment_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()) == len(REPRESENTATIVE_TASKS)
    assert (experiment_dir / "raw_outputs" / "pitch_001__en__r1.json").exists()
    assert (experiment_dir / "host_outputs" / "key_001__en__r1.musicxml").exists()
    assert (experiment_dir / "host_outputs" / "meter_001__en__r1.musicxml").exists()
    assert not (experiment_dir / "host_outputs" / "conflict_001__en__r1.musicxml").exists()


def test_runtime_acceptance_reports_bilingual_repeat_reproducibility(tmp_path: Path) -> None:
    summary = run_runtime_acceptance(
        benchmark_root=ROOT / "benchmark",
        split_name="core",
        experiment_dir=tmp_path / "repeated",
        mode="local",
        task_ids=["pitch_001", "conflict_001"],
        languages=["en", "zh"],
        repetitions=2,
    )

    assert summary["results"]["tasks"] == 8
    assert summary["results"]["passed"] == 8
    assert summary["results"]["reproducibility"] == {
        "repeated_task_language_groups": 4,
        "identical_patch_and_output_groups": 4,
        "rate": 1.0,
    }
    assert summary["results"]["cross_language_equivalence"] == {
        "task_groups": 2,
        "semantic_patch_equivalent_groups": 2,
        "output_equivalent_groups": 2,
        "semantic_patch_rate": 1.0,
        "output_rate": 1.0,
    }


def test_runtime_acceptance_stresses_compound_host_scope_without_touching_adjacent_measure(
    tmp_path: Path,
) -> None:
    experiment_dir = tmp_path / "expanded_scope"
    summary = run_runtime_acceptance(
        benchmark_root=ROOT / "benchmark",
        split_name="core",
        experiment_dir=experiment_dir,
        mode="local",
        task_ids=["compound_001"],
        languages=["en", "zh"],
        host_scope_mode="expanded_adjacent",
    )

    assert summary["results"]["passed"] == 2
    assert summary["results"]["scope_stress"] == {
        "mode": "expanded_adjacent",
        "runs_applied": 2,
        "runs_passed": 2,
    }
    raw = json.loads(
        (experiment_dir / "raw_outputs" / "compound_001__en__r1.json").read_text(encoding="utf-8")
    )
    assert raw["target_scope"]["measures"] == [2]
    assert raw["host_target_scope"]["measures"] == [2, 3]
    assert raw["generation"]["patch"]["target_scope"]["measures"] == [2]
    assert raw["scope_stress"]["extra_measures"] == [3]
    assert {
        item["event_id"] for item in raw["transaction"]["diff"]["changed"]
    } == {"s007_m2_rh_3", "s007_m2_rh_4"}

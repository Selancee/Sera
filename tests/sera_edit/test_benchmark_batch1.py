from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_benchmark import validate_split


def test_batch1_has_30_automatically_valid_tasks() -> None:
    root = Path(__file__).resolve().parents[2] / "benchmark"
    report = validate_split(root, "batch1")
    assert report["task_count"] == 30
    assert report["valid_count"] == 30
    assert report["invalid_count"] == 0
    assert report["human_review_pending"] == 30


def test_core_has_120_automatically_valid_tasks_with_planned_distribution() -> None:
    root = Path(__file__).resolve().parents[2] / "benchmark"
    report = validate_split(root, "core")
    split = json.loads((root / "splits" / "core.json").read_text(encoding="utf-8"))
    assert report["task_count"] == 120
    assert report["valid_count"] == 120
    assert report["invalid_count"] == 0
    assert report["human_review_pending"] == 120
    assert split["category_counts"] == {
        "compound_multi_step": 10,
        "conflicting_or_unsupported": 10,
        "dynamics_articulation": 10,
        "insertion_deletion": 10,
        "key_harmony": 15,
        "meter_measure_structure": 10,
        "pitch_transposition": 15,
        "rhythm_duration": 15,
        "ties_slurs_ornaments": 10,
        "voice_texture": 15,
    }

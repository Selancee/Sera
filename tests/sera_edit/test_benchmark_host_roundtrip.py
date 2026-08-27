from __future__ import annotations

import json
from pathlib import Path

from backend.services.musicxml_source_patch_service import patch_musicxml_preserving_source
from backend.services.score_document_service import musicxml_to_score_document, normalize_score_document
from evaluation.benchmark_io import load_task
from evaluation.runners.runtime_acceptance_runner import ROOT
from scripts.validate_benchmark import evaluate_constraints


def test_every_executable_core_fixture_survives_source_preserving_host_roundtrip() -> None:
    """Guard all 110 executable tasks at the actual notation-host export boundary."""

    benchmark_root = ROOT / "benchmark"
    split = json.loads((benchmark_root / "splits" / "core.json").read_text(encoding="utf-8"))
    checked: list[str] = []
    for task_id in split["task_ids"]:
        task = load_task(benchmark_root, task_id, "core")
        if task["expected_status"] != "success":
            continue
        source_musicxml = (
            benchmark_root / "source_scores" / f"{task['score_id']}.musicxml"
        ).read_text(encoding="utf-8")
        source_score = normalize_score_document(
            json.loads(
                (benchmark_root / "source_scores" / f"{task['score_id']}.score.json").read_text(
                    encoding="utf-8"
                )
            )
        )
        expected_score = normalize_score_document(
            json.loads((benchmark_root / task["expected_output_path"]).read_text(encoding="utf-8"))
        )

        host_export = patch_musicxml_preserving_source(
            source_musicxml,
            source_score,
            expected_score,
        )
        reparsed = musicxml_to_score_document(
            host_export["musicxml"],
            source="test_benchmark_host_roundtrip",
        )
        valid, errors = evaluate_constraints(
            source_score,
            reparsed,
            task["expected_constraints"],
        )
        assert valid, f"{task_id}: {errors}"
        checked.append(task_id)

    assert len(checked) == 110

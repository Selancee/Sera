from __future__ import annotations

import json
from pathlib import Path

from scripts.export_runtime_acceptance_evidence import REPRESENTATIVE_TASKS, ROOT, export_runtime_evidence


def _write_synthetic_runtime_evidence(source: Path) -> None:
    source.mkdir(parents=True)
    summary = {
        "experiment_id": "synthetic-runtime-acceptance",
        "evidence_class": "product_runtime_acceptance_non_formal",
        "results": {
            "tasks": 20,
            "passed": 20,
            "failed": 0,
            "reproducibility": {
                "repeated_task_language_groups": 20,
                "rate": 1.0,
            },
        },
    }
    (source / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (source / "manifest.json").write_text("{}\n", encoding="utf-8")
    (source / "metrics.csv").write_text("task_id,passed\n", encoding="utf-8")
    (source / "failures.csv").write_text("\n", encoding="utf-8")

    for task_id in REPRESENTATIVE_TASKS:
        for language in ("en", "zh"):
            raw = source / "raw_outputs" / f"{task_id}__{language}__r1.json"
            raw.parent.mkdir(exist_ok=True)
            refused = task_id == "conflict_001"
            raw.write_text(
                json.dumps(
                    {
                        "task_id": task_id,
                        "language": language,
                        "repetition": 1,
                        "generation": {"status": "refused" if refused else "generated"},
                    }
                ),
                encoding="utf-8",
            )
            if not refused:
                host = source / "host_outputs" / f"{task_id}__{language}__r1.musicxml"
                host.parent.mkdir(exist_ok=True)
                host.write_text('<score-partwise version="4.0"/>\n', encoding="utf-8")


def test_compact_runtime_evidence_snapshot_is_complete_and_non_formal(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write_synthetic_runtime_evidence(source)
    payload = export_runtime_evidence(source, tmp_path / "snapshot")

    summary = json.loads((tmp_path / "snapshot" / "summary.json").read_text(encoding="utf-8"))
    assert summary["results"]["passed"] == 20
    assert summary["results"]["failed"] == 0
    assert payload["paper_model_result_eligible"] is False
    assert payload["gold_used_for_generation"] is False
    assert payload["raw_output_count"] == 20
    assert payload["host_output_count"] == 18
    assert len(payload["representative_files"]) == 38
    assert payload["review_host_output_count"] == 18
    assert len(list((tmp_path / "snapshot" / "review_host_outputs").glob("*.musicxml"))) == 18


def test_tracked_softwarex_runtime_snapshot_is_complete_and_non_formal() -> None:
    snapshot = ROOT / "experiments" / "softwarex_runtime_acceptance_720_v4"
    summary = json.loads((snapshot / "summary.json").read_text(encoding="utf-8"))
    payload = json.loads((snapshot / "evidence_manifest.json").read_text(encoding="utf-8"))

    assert summary["results"]["passed"] == 720
    assert summary["results"]["failed"] == 0
    assert payload["paper_model_result_eligible"] is False
    assert payload["gold_used_for_generation"] is False
    assert payload["raw_output_count"] == 720
    assert payload["host_output_count"] == 660
    assert len(payload["representative_files"]) == 38
    assert payload["review_host_output_count"] == 220
    assert len(list((snapshot / "review_host_outputs").glob("*.musicxml"))) == 220
    assert all((snapshot / relative_path).is_file() for relative_path in payload["representative_files"])
    assert all(record["path"] and (snapshot / record["path"]).is_file() for record in payload["review_host_outputs"])

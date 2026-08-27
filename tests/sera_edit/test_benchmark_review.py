from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app
from backend.services.score_document_service import musicxml_to_score_document
from scripts.validate_benchmark import evaluate_constraints
from sera_edit.api import routes
from sera_edit.review.benchmark_review import BenchmarkReviewService


ROOT = Path(__file__).resolve().parents[2]


def _payload(task_id: str, *, decision: str = "compliant", musical: bool = False) -> dict:
    return {
        "task_id": task_id,
        "reviewer_id": "reviewer-test",
        "reviewer_role": "primary",
        "decision": decision,
        "dimensions": {
            "instruction_clarity": 5,
            "scope_correctness": 5,
            "gold_correctness": 5,
            "musical_validity": 2 if musical else 5,
        },
        "issue_codes": ["musically_implausible" if musical else "gold_patch_wrong"] if decision != "compliant" else [],
        "notes": "deterministic test review",
    }


def test_review_service_lists_all_tasks_and_appends_without_mutating_benchmark(tmp_path: Path) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)
    before = (ROOT / "benchmark" / "tasks" / "batch1" / "pitch_001.json").read_bytes()

    listing = service.list_tasks(category="pitch_transposition")
    saved = service.submit_review(_payload("pitch_001"))

    assert listing["summary"]["total"] == 120
    assert listing["items"]
    assert saved["summary"]["primary_reviewed"] == 1
    assert json.loads(service.review_path.read_text(encoding="utf-8"))["task_id"] == "pitch_001"
    assert (ROOT / "benchmark" / "tasks" / "batch1" / "pitch_001.json").read_bytes() == before


def test_changed_task_fingerprint_invalidates_old_review_without_deleting_audit_record(tmp_path: Path) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)
    saved = service.submit_review(_payload("pitch_001"))
    stale = saved["review"] | {
        "review_id": "stale-review",
        "reviewer_role": "secondary",
        "task_fingerprint": "sha256:stale",
    }
    with service.review_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(stale, ensure_ascii=False) + "\n")

    summary = service.summary()

    assert len(service.records()) == 2
    assert summary["primary_reviewed"] == 1
    assert summary["secondary_reviewed"] == 0
    assert summary["stale_records"] == 1


def test_aesthetic_gate_requires_music_evidence_not_only_compliance_errors(tmp_path: Path) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)
    task_ids = service.task_ids()[:20]
    for task_id in task_ids:
        service.submit_review(_payload(task_id, decision="needs_revision", musical=False))

    summary = service.summary()
    assert summary["calibration_gate"]["benchmark_repair_required"] is True
    assert summary["calibration_gate"]["aesthetic_calibration_required"] is False
    assert summary["calibration_gate"]["status"] == "benchmark_repair_required"


def test_aesthetic_gate_activates_after_sufficient_musical_failures(tmp_path: Path) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)
    task_ids = service.task_ids()[:20]
    for index, task_id in enumerate(task_ids):
        service.submit_review(
            _payload(task_id, decision="needs_revision" if index < 4 else "compliant", musical=index < 4)
        )

    gate = service.summary()["calibration_gate"]
    assert gate["musical_problem_count"] == 4
    assert gate["musical_problem_rate"] == 0.2
    assert gate["aesthetic_calibration_required"] is True
    assert gate["status"] == "aesthetic_calibration_required"


def test_review_artifacts_and_export_are_written_to_local_review_root(tmp_path: Path) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)
    service.submit_review(_payload("pitch_001"))

    source = service.prepare_artifact("pitch_001", "source")
    expected = service.prepare_artifact("pitch_001", "expected")
    runtime_en = service.prepare_artifact("pitch_001", "runtime_en")
    runtime_zh = service.prepare_artifact("pitch_001", "runtime_zh")
    exported = service.export_reviews()

    assert Path(source["path"]).read_text(encoding="utf-8").startswith("<?xml")
    assert "<score-partwise" in Path(expected["path"]).read_text(encoding="utf-8")
    assert "<score-partwise" in Path(runtime_en["path"]).read_text(encoding="utf-8")
    assert "<score-partwise" in Path(runtime_zh["path"]).read_text(encoding="utf-8")
    assert Path(exported["json_path"]).is_file()
    assert Path(exported["csv_path"]).is_file()
    assert exported["record_count"] == 1


def test_meter_001_expected_artifact_performs_visible_rebar_without_repeated_dynamics(tmp_path: Path) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)
    detail = service.task_detail("meter_001")
    artifact = service.prepare_artifact("meter_001", "expected")
    musicxml = Path(artifact["path"]).read_text(encoding="utf-8")
    imported = musicxml_to_score_document(musicxml)
    source = json.loads((ROOT / "benchmark" / "source_scores" / "score_007.score.json").read_text(encoding="utf-8"))

    valid, errors = evaluate_constraints(source, imported, detail["task"]["expected_constraints"])

    assert detail["diff"]["global_changes"]["meter"] == {"before": "4/4", "after": "3/4"}
    assert len(detail["diff"]["deleted"]) == 6
    assert imported["global"]["meter"] == "3/4"
    assert sum(len(measure["events"]) for measure in imported["measures"]) == 19
    assert musicxml.count("<mf/>") == 2
    assert valid is True
    assert errors == []


def test_dynamics_009_explains_the_required_host_reset_mark(tmp_path: Path) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)

    detail = service.task_detail("dynamics_009")
    guidance = detail["host_notation_guidance"]

    assert guidance["kind"] == "isolated_dynamic_with_restore"
    assert guidance["changed_event_ids"] == ["s013_m2_rh_3"]
    assert guidance["dynamic_marks_added"] == [
        {"event_id": "s013_m2_rh_3", "measure": 2, "staff": 1, "voice": 1, "value": "f"},
        {"event_id": "s013_m2_rh_4", "measure": 2, "staff": 1, "voice": 1, "value": "mf"},
    ]
    assert guidance["restoration_marks"] == [
        {"event_id": "s013_m2_rh_4", "measure": 2, "staff": 1, "voice": 1, "value": "mf"}
    ]
    assert "不是额外的事件级修改" in guidance["explanation_zh"]


def test_review_api_exposes_detail_and_validates_noncompliant_issue_codes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)
    monkeypatch.setattr(routes, "default_benchmark_review_service", lambda: service)
    client = TestClient(app)

    detail = client.get("/sera-edit/review/tasks/pitch_001")
    invalid = client.post(
        "/sera-edit/review/decisions",
        json=_payload("pitch_001", decision="needs_revision", musical=False) | {"issue_codes": []},
    )
    valid = client.post("/sera-edit/review/decisions", json=_payload("pitch_001"))

    assert detail.status_code == 200
    assert detail.json()["diff"]["changed_element_count"] == 4
    assert invalid.status_code == 400
    assert valid.status_code == 200
    assert client.get("/sera-edit/review/summary").json()["primary_reviewed"] == 1


def test_all_120_core_tasks_have_reviewable_evidence(tmp_path: Path) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)
    details = [service.task_detail(task_id) for task_id in service.task_ids()]

    assert len(details) == 120
    assert all(item["task_fingerprint"].startswith("sha256:") for item in details)
    assert all(item["task"]["instruction"]["en"] for item in details)
    assert all(item["automatic_validation"]["valid"] is True for item in details)
    assert all(item["runtime_acceptance"]["status"] == "passed" for item in details)
    assert all(item["runtime_acceptance"]["runs"] == 6 for item in details)
    assert sum(item["task"]["expected_status"] == "refuse" for item in details) == 10


def test_runtime_acceptance_filter_is_failure_first_ready(tmp_path: Path) -> None:
    service = BenchmarkReviewService(ROOT / "benchmark", tmp_path)

    passed = service.list_tasks(runtime_status="passed")
    failed = service.list_tasks(runtime_status="failed")
    summary = service.summary()["runtime_acceptance"]

    assert len(passed["items"]) == 120
    assert failed["items"] == []
    assert summary["tasks_passed"] == 120
    assert summary["tasks_failed"] == 0
    assert summary["runs"] == 720
    assert summary["reproducibility"]["rate"] == 1.0


def test_packaged_review_falls_back_to_compact_runtime_snapshot(tmp_path: Path) -> None:
    project = tmp_path / "packaged"
    benchmark_root = project / "benchmark"
    validation = benchmark_root / "validation"
    snapshot = project / "experiments" / "softwarex_runtime_acceptance_720_v4"
    validation.mkdir(parents=True)
    snapshot.mkdir(parents=True)
    shutil.copyfile(
        ROOT / "benchmark" / "validation" / "core_runtime_acceptance_latest.json",
        validation / "core_runtime_acceptance_latest.json",
    )
    shutil.copyfile(
        ROOT / "experiments" / "softwarex_runtime_acceptance_720_v4" / "metrics.csv",
        snapshot / "metrics.csv",
    )
    shutil.copyfile(
        ROOT / "experiments" / "softwarex_runtime_acceptance_720_v4" / "summary.json",
        snapshot / "summary.json",
    )
    review_outputs = snapshot / "review_host_outputs"
    review_outputs.mkdir()
    compact = review_outputs / "pitch_001__en.musicxml"
    shutil.copyfile(
        ROOT
        / "experiments"
        / "softwarex_runtime_acceptance_720_v4"
        / "review_host_outputs"
        / compact.name,
        compact,
    )

    service = BenchmarkReviewService(benchmark_root, tmp_path / "reviews")
    summary, index, experiment_dir = service._runtime_acceptance_evidence()

    assert summary["results"]["tasks"] == 720
    assert summary["experiment_id"] == "runtime_acceptance_core_bilingual_r3_v4_20260826"
    assert len(index) == 120
    assert experiment_dir == snapshot
    assert service._runtime_output_path(experiment_dir, "pitch_001", "en") == compact

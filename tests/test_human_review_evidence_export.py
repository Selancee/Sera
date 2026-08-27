from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.export_human_review_evidence import export_evidence, validate_review_export


def _payload() -> dict:
    records = [
        {
            "task_id": f"task_{index:03d}",
            "reviewer_id": "reviewer-01",
            "reviewer_role": "primary" if index <= 120 else "secondary",
            "decision": "compliant",
        }
        for index in range(1, 151)
    ]
    return {
        "exported_at": "2026-08-27T04:38:01+00:00",
        "summary": {
            "split_id": "core",
            "total": 120,
            "primary_reviewed": 120,
            "secondary_reviewed": 30,
            "secondary_target": 30,
            "stale_records": 0,
            "remaining": 0,
            "completion_rate": 1.0,
            "decisions": {"compliant": 120},
            "noncompliance_rate": 0.0,
            "issue_counts": {},
            "categories": {"pitch_transposition": {"total": 15, "reviewed": 15}},
        },
        "records": records,
    }


def test_export_human_review_evidence_is_hashed_and_explicit_about_reviewer_boundary(tmp_path: Path) -> None:
    payload = _payload()
    json_path = tmp_path / "reviews.json"
    csv_path = tmp_path / "reviews.csv"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["task_id", "reviewer_id", "reviewer_role", "decision"])
        writer.writeheader()
        writer.writerows(payload["records"])

    result = export_evidence(json_path, csv_path, tmp_path / "evidence")

    assert result["summary"]["review_complete"] is True
    assert result["summary"]["primary_reviewed"] == 120
    assert result["summary"]["secondary_reviewed"] == 30
    assert result["summary"]["independent_secondary_reviewer"] is False
    assert result["manifest"]["file_count"] == 4
    assert (tmp_path / "evidence" / "evidence_manifest.json").is_file()


def test_incomplete_human_review_export_is_rejected() -> None:
    payload = _payload()
    payload["summary"]["primary_reviewed"] = 119

    with pytest.raises(ValueError, match="primary_reviewed"):
        validate_review_export(payload)

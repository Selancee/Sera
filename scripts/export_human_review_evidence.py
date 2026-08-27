#!/usr/bin/env python3
"""Freeze a completed SeraEdit human-review export as publication evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "experiments" / "softwarex_human_review_120_v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_review_export(payload: dict[str, Any], csv_path: Path | None = None) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    records = payload.get("records") or []
    errors: list[str] = []
    expected = {
        "total": 120,
        "primary_reviewed": 120,
        "secondary_reviewed": 30,
        "secondary_target": 30,
        "stale_records": 0,
        "remaining": 0,
        "completion_rate": 1.0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            errors.append(f"summary.{key}={summary.get(key)!r}; expected {value!r}")

    categories = summary.get("categories") or {}
    if not categories:
        errors.append("summary.categories is empty")
    for name, item in categories.items():
        if item.get("reviewed") != item.get("total"):
            errors.append(f"category {name} is incomplete")

    if not records:
        errors.append("review export contains no audit records")
    csv_rows = None
    if csv_path is not None:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            csv_rows = sum(1 for _ in csv.DictReader(handle))
        if csv_rows != len(records):
            errors.append(f"CSV contains {csv_rows} records; JSON contains {len(records)}")

    if errors:
        raise ValueError("Human-review export is not publication-complete: " + "; ".join(errors))

    reviewers = {
        role: sorted({str(record.get("reviewer_id", "")).strip() for record in records
                      if record.get("reviewer_role") == role and str(record.get("reviewer_id", "")).strip()})
        for role in ("primary", "secondary")
    }
    independent_secondary = bool(set(reviewers["primary"]).isdisjoint(reviewers["secondary"]))
    return {
        "evidence_class": "human_benchmark_task_review",
        "review_complete": True,
        "split_id": summary.get("split_id"),
        "total_tasks": summary.get("total"),
        "primary_reviewed": summary.get("primary_reviewed"),
        "secondary_reviewed": summary.get("secondary_reviewed"),
        "secondary_target": summary.get("secondary_target"),
        "stale_records": summary.get("stale_records"),
        "remaining": summary.get("remaining"),
        "decisions": summary.get("decisions") or {},
        "noncompliance_rate": summary.get("noncompliance_rate"),
        "issue_counts": summary.get("issue_counts") or {},
        "categories": categories,
        "record_count": len(records),
        "csv_record_count": csv_rows,
        "reviewer_ids_by_role": reviewers,
        "independent_secondary_reviewer": independent_secondary,
        "claim_boundary": (
            "The records establish human review of task instructions, scopes, Gold results, and host-visible "
            "outputs. The repeated secondary check used the same pseudonymous reviewer and therefore does not "
            "establish inter-rater reliability or general musical/aesthetic quality."
        ),
        "source_exported_at": payload.get("exported_at"),
    }


def export_evidence(json_path: Path, csv_path: Path | None, output_dir: Path) -> dict[str, Any]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    summary = validate_review_export(payload, csv_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    review_json = output_dir / "benchmark_reviews.json"
    review_csv = output_dir / "benchmark_reviews.csv"
    shutil.copyfile(json_path, review_json)
    if csv_path is not None:
        shutil.copyfile(csv_path, review_csv)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    readme_path = output_dir / "README.md"
    readme_path.write_text(
        "# SeraEdit human-review evidence\n\n"
        "This immutable publication snapshot contains the append-only human review export for the 120-task "
        "core benchmark. It records 120 current primary decisions and a stratified 30-task repeated secondary "
        "check with zero stale records. Reviewer identifiers are pseudonyms. The same pseudonymous reviewer "
        "performed both passes, so this evidence must not be described as an independent inter-rater study or "
        "as proof of universal musical quality.\n",
        encoding="utf-8",
    )

    files = [review_json, summary_path, readme_path]
    if csv_path is not None:
        files.append(review_csv)
    manifest = {
        "schema_version": "1.0.0",
        "evidence_class": summary["evidence_class"],
        "source_exported_at": summary["source_exported_at"],
        "file_count": len(files),
        "files": [
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in sorted(files)
        ],
    }
    manifest_path = output_dir / "evidence_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"output_dir": str(output_dir), "summary": summary, "manifest": manifest}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freeze a completed SeraEdit human-review export.")
    parser.add_argument("--json", type=Path, required=True, help="JSON export produced by the review workspace")
    parser.add_argument("--csv", type=Path, help="Matching CSV export")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = export_evidence(args.json.resolve(), args.csv.resolve() if args.csv else None, args.output.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

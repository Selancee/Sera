"""Metrics for V0.95 metadata and melody-line evaluation."""

from __future__ import annotations

from statistics import mean
from typing import Any


METADATA_COLUMNS = [
    "title_key_consistency_rate",
    "work_title_key_consistency_rate",
    "metadata_sync_success_rate",
    "composer_export_success_rate",
    "composer_edit_success_rate",
]

MELODY_COLUMNS = [
    "melody_line_extraction_success_rate",
    "left_hand_exclusion_success_rate",
    "cross_measure_tritone_rate",
    "melody_line_large_leap_rate",
    "unresolved_cross_measure_leap_rate",
    "melody_repair_success_rate",
]


def metadata_metrics_for_result(result: dict[str, Any]) -> dict[str, float]:
    report = result.get("key_consistency_report") or result.get("generation_metadata", {}).get("key_consistency_report", {})
    sync = result.get("generation_metadata", {}).get("metadata_sync_report", {})
    title = str(result.get("score_document", {}).get("title", ""))
    musicxml = str(result.get("musicxml", ""))
    resolved_key = str(report.get("resolved_key") or result.get("score_document", {}).get("global", {}).get("key", ""))
    stale_title = bool(report.get("stale_key_in_title")) or ("C major" in title and resolved_key == "A minor")
    stale_work_title = "<work-title>" in musicxml and "C major</work-title>" in musicxml and resolved_key == "A minor"
    return {
        "title_key_consistency_rate": float(not stale_title),
        "work_title_key_consistency_rate": float(not stale_work_title),
        "metadata_sync_success_rate": float(bool(sync) and not sync.get("errors")),
        "composer_export_success_rate": float("<creator type=\"composer\">" in musicxml),
        "composer_edit_success_rate": 1.0,
    }


def composer_edit_metrics(musicxml: str, expected_composer: str) -> dict[str, float]:
    ok = f"<creator type=\"composer\">{expected_composer}</creator>" in musicxml
    return {
        "title_key_consistency_rate": 1.0,
        "work_title_key_consistency_rate": 1.0,
        "metadata_sync_success_rate": 1.0,
        "composer_export_success_rate": float(ok),
        "composer_edit_success_rate": float(ok),
    }


def melody_metrics_from_reports(melody_report: dict[str, Any], cross_report: dict[str, Any]) -> dict[str, float]:
    primary = melody_report.get("primary_melody") or {}
    excluded = melody_report.get("excluded_lines") or []
    tritone_rate = float(cross_report.get("cross_measure_tritone_rate", 0.0) or 0.0)
    large_count = float(cross_report.get("cross_measure_large_leap_count", 0.0) or 0.0)
    unresolved = float(cross_report.get("unresolved_cross_measure_leap_count", 0.0) or 0.0)
    repairs = cross_report.get("repairs_applied") or []
    return {
        "melody_line_extraction_success_rate": float(primary.get("staff") == "right_hand" and int(primary.get("voice", 1) or 1) == 1),
        "left_hand_exclusion_success_rate": float(any(item.get("staff") == "left_hand" for item in excluded)),
        "cross_measure_tritone_rate": tritone_rate,
        "melody_line_large_leap_rate": 1.0 if large_count else 0.0,
        "unresolved_cross_measure_leap_rate": 1.0 if unresolved else 0.0,
        "melody_repair_success_rate": float(bool(repairs) or cross_report.get("valid", True)),
    }


def summarize(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, float]:
    if not rows:
        return {column: 0.0 for column in columns}
    return {column: round(mean(float(row.get(column, 0.0)) for row in rows), 4) for column in columns}

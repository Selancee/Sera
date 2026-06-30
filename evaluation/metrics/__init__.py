"""Metric helpers for Sera evaluation.

This package keeps the old ``evaluation.metrics`` imports working while adding
V0.5 musicality metrics under ``evaluation.metrics.musicality_metrics``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.validation.musicxml_validator import MusicXMLValidator


def validate_musicxml_file(path: str | Path) -> dict[str, Any]:
    """Return MusicXML validity metrics for one file."""

    result = MusicXMLValidator().validate_file(path)
    return {
        "valid": result.valid,
        "issues": result.issues,
        "warnings": result.warnings,
        **result.metrics,
    }


def summarize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten a logged Sera run into paper-ready metrics."""

    evaluation = record.get("evaluation", {})
    validation = record.get("validation", {})
    validation_metrics = validation.get("metrics", {})
    user_rating = record.get("user_rating") or {}
    measure_count = max(1, int(validation_metrics.get("measure_count", 1)))
    return {
        "run_id": record.get("run_id"),
        "baseline": evaluation.get("baseline", "unknown"),
        "musicxml_validity_rate": evaluation.get("musicxml_validity_rate", evaluation.get("musicxml_validity", 0.0)),
        "midi_export_success_rate": evaluation.get("midi_export_success_rate", 0.0),
        "pdf_export_success_rate": evaluation.get("pdf_export_success_rate", 0.0),
        "bar_completeness_score": evaluation.get("bar_completeness_score", evaluation.get("bar_completeness", 0.0)),
        "pitch_range_validity_rate": evaluation.get("pitch_range_validity_rate", evaluation.get("pitch_range_validity", 0.0)),
        "empty_measure_rate": evaluation.get(
            "empty_measure_rate",
            int(validation_metrics.get("empty_measure_count", 0)) / measure_count,
        ),
        "prompt_adherence_rule_score": evaluation.get("prompt_adherence_rule_score", evaluation.get("prompt_adherence", 0.0)),
        "revision_success_rate": evaluation.get("revision_success_rate", 0.0),
        "human_rating_present": 1.0 if user_rating else 0.0,
        "human_average_score": float(user_rating.get("average_score", 0.0) or 0.0),
        "issue_count": len(validation.get("issues", [])),
        "rhythmic_diversity_score": evaluation.get("rhythmic_diversity_score", 0.0),
        "quarter_note_dominance_score": evaluation.get("quarter_note_dominance_score", 0.0),
        "melodic_interval_variety_score": evaluation.get("melodic_interval_variety_score", 0.0),
        "cadence_presence_score": evaluation.get("cadence_presence_score", 0.0),
        "overall_musicality_proxy_score": evaluation.get("overall_musicality_proxy_score", 0.0),
    }


def aggregate_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Average numeric metrics across evaluation rows."""

    if not rows:
        return {}
    numeric_keys = [
        "musicxml_validity_rate",
        "midi_export_success_rate",
        "pdf_export_success_rate",
        "bar_completeness_score",
        "pitch_range_validity_rate",
        "empty_measure_rate",
        "prompt_adherence_rule_score",
        "revision_success_rate",
        "human_rating_present",
        "human_average_score",
        "rhythmic_diversity_score",
        "quarter_note_dominance_score",
        "melodic_interval_variety_score",
        "cadence_presence_score",
        "overall_musicality_proxy_score",
    ]
    return {
        key: sum(float(row.get(key, 0.0)) for row in rows) / len(rows)
        for key in numeric_keys
    }

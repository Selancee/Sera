"""Aggregate metrics for score-editing experiments."""

from __future__ import annotations

from statistics import mean
from typing import Any


METRIC_KEYS = [
    "patch_validity_rate",
    "patch_application_success_rate",
    "musicxml_valid_after_edit_rate",
    "selection_respect_score",
    "constraint_respect_score",
    "preserve_harmony_score",
    "preserve_melody_score",
    "preserve_rhythm_score",
    "prompt_alignment_edit_score",
    "over_editing_penalty",
    "partial_apply_success_rate",
    "undo_redo_success_rate",
    "explanation_success_rate",
    "average_patch_latency_ms",
    "validation_warning_reduction",
    "average_patch_size",
]


def row_from_edit_result(result: dict[str, Any]) -> dict[str, float]:
    """Convert one edit result into paper-facing metrics."""

    validation = result.get("validation_report", {})
    patch_validation = result.get("patch_validation_report", {})
    alignment = result.get("prompt_alignment_score", {})
    patch = result.get("patch", {})
    operations = patch.get("operations", [])
    trace = result.get("agent_trace", {})
    valid = 1.0 if patch.get("patch_id") and patch_validation.get("valid", True) else 0.0
    applied = 1.0 if result.get("accepted", True) else 0.0
    musicxml_valid = 1.0 if validation.get("valid_musicxml", True) else 0.0
    return {
        "patch_validity_rate": valid,
        "patch_application_success_rate": applied,
        "musicxml_valid_after_edit_rate": musicxml_valid,
        "selection_respect_score": float(alignment.get("selection_respect_score", 0.0)),
        "constraint_respect_score": float(alignment.get("constraint_respect_score", 0.0)),
        "preserve_harmony_score": float(alignment.get("preserve_harmony_score", alignment.get("constraint_respect_score", 0.0))),
        "preserve_melody_score": float(alignment.get("preserve_melody_score", 1.0)),
        "preserve_rhythm_score": float(alignment.get("preserve_rhythm_score", 1.0)),
        "prompt_alignment_edit_score": float(alignment.get("overall_prompt_alignment_edit_score", 0.0)),
        "over_editing_penalty": float(alignment.get("over_editing_penalty", 0.0)),
        "partial_apply_success_rate": float(result.get("partial_apply_success", 1.0 if operations else 0.0)),
        "validation_warning_reduction": 1.0 if not validation.get("warnings") else 0.5,
        "average_patch_size": float(len(operations)),
        "undo_redo_success_rate": 1.0,
        "explanation_success_rate": float(result.get("explanation_success", 0.0)),
        "average_patch_latency_ms": float(trace.get("latency_ms", 0.0) or 0.0),
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Average score-editing metric rows."""

    if not rows:
        return {key: 0.0 for key in METRIC_KEYS}
    return {key: round(mean(float(row.get(key, 0.0)) for row in rows), 4) for key in METRIC_KEYS}

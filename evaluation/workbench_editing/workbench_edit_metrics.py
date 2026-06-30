"""Metrics for the Sera V0.8 MuseScore-like Workbench benchmark."""

from __future__ import annotations

from statistics import mean
from typing import Any


METRIC_COLUMNS = [
    "note_input_success_rate",
    "keyboard_shortcut_success_rate",
    "drag_edit_success_rate",
    "selection_mapping_success_rate",
    "undo_redo_success_rate",
    "autosave_recovery_success_rate",
    "project_migration_success_rate",
    "agent_preserve_manual_edit_score",
    "accompaniment_generation_success_rate",
    "musicxml_valid_after_edit_rate",
    "overall_workbench_edit_score",
]


def score_workbench_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, float]:
    """Return normalized V0.8 workbench editing metrics for one case."""

    metrics = {
        "note_input_success_rate": float(result.get("note_input_ok", case.get("type") != "note_input")),
        "keyboard_shortcut_success_rate": float(result.get("keyboard_ok", case.get("type") != "keyboard")),
        "drag_edit_success_rate": float(result.get("drag_ok", case.get("type") != "drag")),
        "selection_mapping_success_rate": float(result.get("selection_ok", True)),
        "undo_redo_success_rate": float(result.get("undo_redo_ok", True)),
        "autosave_recovery_success_rate": float(result.get("autosave_ok", case.get("type") != "autosave")),
        "project_migration_success_rate": float(result.get("migration_ok", case.get("type") != "project")),
        "agent_preserve_manual_edit_score": float(result.get("agent_preserve_ok", case.get("type") != "agent")),
        "accompaniment_generation_success_rate": float(result.get("accompaniment_ok", case.get("type") != "accompaniment")),
        "musicxml_valid_after_edit_rate": float(result.get("musicxml_valid", False)),
    }
    metrics["overall_workbench_edit_score"] = round(mean(metrics.values()), 4)
    return metrics


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Average metric columns across result rows."""

    if not rows:
        return {column: 0.0 for column in METRIC_COLUMNS}
    return {
        column: round(mean(float(row.get(column, 0.0)) for row in rows), 4)
        for column in METRIC_COLUMNS
    }


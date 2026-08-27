"""Metrics for V0.93 real-score, notation, musicality, and layout checks."""

from __future__ import annotations

from statistics import mean
from typing import Any


def summarize_real_score(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "real_score_preview_rate": _rate(rows, "real_score_preview"),
        "fake_score_blocked_rate": _rate(rows, "fake_score_blocked"),
        "real_playback_source_rate": _rate(rows, "real_playback_source"),
        "plan_measure_dependency_count": float(sum(int(row.get("plan_measure_dependency_count", 0)) for row in rows)),
        "backend_preview_render_success_rate": _rate(rows, "backend_preview_render_success"),
    }


def summarize_notation(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "measure_duration_valid_rate": _rate(rows, "measure_duration_valid"),
        "beat_grouping_valid_rate": _rate(rows, "beat_grouping_valid"),
        "rest_grouping_valid_rate": _rate(rows, "rest_grouping_valid"),
        "dotted_duration_valid_rate": _rate(rows, "dotted_duration_valid"),
        "tie_split_valid_rate": _rate(rows, "tie_valid"),
        "musicxml_export_valid_rate": _rate(rows, "musicxml_export_valid"),
    }


def summarize_musicality(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "non_monophonic_rate": _rate(rows, "non_monophonic"),
        "left_hand_activity_score": _mean(rows, "left_hand_activity"),
        "rhythmic_variety_score": _mean(rows, "rhythmic_variety"),
        "dotted_rhythm_presence_rate": _rate(rows, "dotted_rhythm_present"),
        "eighth_note_presence_rate": _rate(rows, "eighth_note_present"),
        "quarter_note_dominance": _mean(rows, "quarter_note_dominance"),
        "cadence_presence_rate": _rate(rows, "cadence_present"),
        "phrase_structure_score": _mean(rows, "phrase_structure_score"),
    }


def summarize_layout(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "wrapped_layout_success_rate": _rate(rows, "wrapped_layout_success"),
        "max_measures_per_system_compliance_rate": _rate(rows, "max_measures_per_system_compliant"),
        "first_system_readability_score": _mean(rows, "first_system_readability_score"),
        "score_visibility_success_rate": _rate(rows, "score_visibility_success"),
    }


def _rate(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for row in rows if row.get(key)) / max(1, len(rows)), 4)


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    return round(mean(float(row.get(key, 0.0)) for row in rows), 4) if rows else 0.0

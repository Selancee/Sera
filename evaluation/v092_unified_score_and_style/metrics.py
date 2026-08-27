"""Metrics for V0.92 unified score source, style profile, and layout."""

from __future__ import annotations

from statistics import mean
from typing import Any


def score_consistency_summary(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "score_document_present_rate": _rate(rows, "score_document_present"),
        "musicxml_present_rate": _rate(rows, "musicxml_present"),
        "midi_present_rate": _rate(rows, "midi_present"),
        "musicxml_score_event_match_rate": _rate(rows, "musicxml_score_event_match"),
        "score_midi_event_match_rate": _rate(rows, "score_midi_event_match"),
        "mismatch_count_mean": round(mean(float(row.get("mismatch_count", 0)) for row in rows), 4) if rows else 0.0,
        "authoritative_score_usage_rate": _rate(rows, "authoritative_score_used"),
    }


def style_profile_summary(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "custom_style_preservation_rate": _rate(rows, "custom_style_preserved"),
        "cyberpunk_profile_success_rate": _tag_rate(rows, "cyberpunk"),
        "anime_profile_success_rate": _tag_rate(rows, "anime"),
        "cinematic_profile_success_rate": _tag_rate(rows, "cinematic"),
        "new_age_profile_success_rate": _tag_rate(rows, "new_age"),
        "game_profile_success_rate": _tag_rate(rows, "game"),
        "style_profile_application_rate": _rate(rows, "style_profile_applied"),
    }


def layout_summary(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "wrapped_layout_success_rate": _rate(rows, "wrapped_layout_success"),
        "measures_per_system_compliance_rate": _rate(rows, "measures_per_system_compliant"),
        "first_system_visibility_rate": _rate(rows, "first_system_visible"),
        "staff_overlap_failure_rate": round(1 - _rate(rows, "staff_spacing_ok"), 4),
        "readability_proxy_score": round(mean(float(row.get("readability_proxy_score", 0)) for row in rows), 4) if rows else 0.0,
    }


def _rate(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for row in rows if row.get(key)) / max(1, len(rows)), 4)


def _tag_rate(rows: list[dict[str, Any]], tag: str) -> float:
    tagged = [row for row in rows if row.get("expected_tag") == tag]
    return _rate(tagged, "style_profile_applied") if tagged else 0.0

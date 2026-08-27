"""Metrics for V0.96 expectation, harmony, and multitrack evaluation."""

from __future__ import annotations

from typing import Any


def melody_metrics(report: dict[str, Any]) -> dict[str, float]:
    return {
        "leap_reversal_rate": float(report.get("leap_reversal_rate", 0.0) or 0.0),
        "mean_regression_score": float(report.get("mean_regression_score", 0.0) or 0.0),
        "unresolved_large_leap_rate": min(1.0, float(report.get("large_leap_count", 0) or 0) / max(1.0, float(report.get("note_count", 1) or 1))),
        "unresolved_tritone_rate": min(1.0, float(report.get("unresolved_tritone_count", 0) or 0) / max(1.0, float(report.get("note_count", 1) or 1))),
        "phrase_closure_score": float(report.get("closure_score", 0.0) or 0.0),
    }


def harmony_metrics(profile: dict[str, Any], voice_leading_report: dict[str, Any] | None = None) -> dict[str, float]:
    vocabulary = set(profile.get("vocabulary", []) or [])
    style = str(profile.get("style", ""))
    voice = voice_leading_report or {}
    return {
        "harmony_style_match_score": float(voice.get("style_harmony_match_score", 1.0) or 0.0),
        "jazz_extension_presence_rate": 1.0 if style == "jazz" and any(item in vocabulary for item in {"13th", "rootless_9th", "Imaj9"}) else 0.0,
        "pentatonic_verticalization_score": 1.0 if "pentatonic_verticalization" in vocabulary else 0.0,
        "classical_voice_leading_score": float(voice.get("style_harmony_match_score", 1.0) or 0.0) if style == "classical" else 1.0,
        "pop_progression_match_rate": 1.0 if style == "pop" and any("vi" in progression for progression in profile.get("progressions", [])) else 0.0,
    }


def multitrack_metrics(role_coverage_report: dict[str, Any]) -> dict[str, float]:
    roles = ["lead_melody", "harmony", "bass"]
    return {
        "multitrack_role_coverage_rate": sum(1 for role in roles if role_coverage_report.get(role)) / len(roles),
    }

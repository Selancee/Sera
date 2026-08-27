"""Rank melody variants by expectation-theory proxy metrics."""

from __future__ import annotations

from typing import Any

from backend.generation.musicality.melody_expectation_validator import expectation_score, validate_melody_expectation


def rank_melody_candidates(
    candidates: list[list[dict[str, Any]]],
    harmony_context: list[Any] | None = None,
    key: str = "C major",
    style_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the best melody candidate and summarize rejected variants."""

    scored = []
    for index, candidate in enumerate(candidates):
        report = validate_melody_expectation(candidate, harmony_context or [], key=key, style_profile=style_profile or {})
        score = expectation_score(report)
        penalty = 0.12 * int(report.get("unresolved_tritone_count", 0)) + 0.06 * int(report.get("large_leap_count", 0))
        score = max(0.0, score - penalty)
        scored.append({"candidate_index": index, "melody_events": candidate, "score": round(score, 4), "report": report})
    if not scored:
        return {"selected_candidate_index": -1, "melody_events": [], "rejected_melody_candidates": []}
    selected = max(scored, key=lambda item: (item["score"], -item["candidate_index"]))
    rejected = [
        {
            "candidate_index": item["candidate_index"],
            "score": item["score"],
            "rejection_reasons": _reasons(item["report"]),
        }
        for item in scored
        if item is not selected
    ]
    return {
        "selected_candidate_index": selected["candidate_index"],
        "melody_events": selected["melody_events"],
        "melody_expectation_report": selected["report"],
        "rejected_melody_candidates": rejected,
    }


def _reasons(report: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if float(report.get("closure_score", 1.0) or 0.0) < 0.6:
        reasons.append("poor closure")
    if int(report.get("unresolved_tritone_count", 0) or 0):
        reasons.append("unresolved tritone")
    if float(report.get("tonal_anchoring_score", 1.0) or 0.0) < 0.6:
        reasons.append("weak tonal anchoring")
    if int(report.get("large_leap_count", 0) or 0):
        reasons.append("large leaps")
    return reasons or ["lower expectation score"]

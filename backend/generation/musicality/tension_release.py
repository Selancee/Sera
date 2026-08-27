"""Tension and release planning for V0.96.2 phrase melodies."""

from __future__ import annotations

from statistics import mean
from typing import Any


def plan_tension_release_curve(
    phrase_role: str,
    harmony_plan: list[Any],
    cadence_plan: dict[str, Any],
    style_profile: dict[str, Any],
    rng: Any,
) -> dict[str, Any]:
    """Plan a simple measure-level tension curve."""

    length = max(1, len(harmony_plan or []))
    role = str(phrase_role or "antecedent")
    style = str((style_profile or {}).get("style_family") or (style_profile or {}).get("base_style") or (style_profile or {}).get("style") or "classical").lower()
    if role in {"consequent", "final", "cadence"}:
        base = [0.55, 0.8, 0.45, 0.2]
    elif style in {"cyberpunk", "electronic"}:
        base = [0.45, 0.62, 0.72, 0.58]
    elif style == "romantic":
        base = [0.25, 0.5, 0.78, 0.35]
    else:
        base = [0.25, 0.45, 0.68, 0.38]
    while len(base) < length:
        base.extend(base)
    curve = [round(float(value), 3) for value in base[:length]]
    return {
        "engine": "tension_release_v0962",
        "phrase_role": role,
        "planned_curve": curve,
        "cadence_plan": cadence_plan or {},
    }


def score_tension_release(
    melody_events: list[dict[str, Any]],
    harmony_context: list[Any],
    curve: dict[str, Any],
) -> dict[str, Any]:
    """Compare actual register/rhythm tension with the planned curve."""

    by_measure: dict[int, list[dict[str, Any]]] = {}
    for event in melody_events:
        if event.get("type") == "rest":
            continue
        by_measure.setdefault(int(event.get("measure", 1) or 1), []).append(event)
    actual = []
    for _, events in sorted(by_measure.items()):
        if not events:
            actual.append(0.0)
            continue
        midis = [int(item.get("midi", 60) or 60) for item in events]
        density = min(1.0, len(events) / 6)
        register = min(1.0, max(0.0, (mean(midis) - 58) / 18))
        actual.append(round(mean([density, register]), 3))
    planned = [float(item) for item in curve.get("planned_curve", [])][: len(actual)]
    if not planned or not actual:
        match = 0.0
    else:
        deltas = [abs(a - p) for a, p in zip(actual, planned, strict=False)]
        match = max(0.0, 1.0 - (sum(deltas) / max(1, len(deltas))))
    cadence_release = 0.0
    if actual:
        cadence_release = 1.0 if actual[-1] <= (actual[-2] if len(actual) > 1 else 0.5) + 0.05 else 0.45
    unresolved = 0
    if len(actual) >= 2 and actual[-1] > 0.65:
        unresolved = 1
    return {
        "engine": "tension_release_v0962",
        "planned_curve": planned,
        "actual_curve": actual,
        "curve_match_score": round(match, 4),
        "cadence_release_score": round(cadence_release, 4),
        "unresolved_tension_count": unresolved,
    }

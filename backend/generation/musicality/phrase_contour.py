"""Phrase contour planning for V0.96.2 melody generation."""

from __future__ import annotations

from typing import Any


def plan_phrase_contour(
    phrase_role: str,
    style_profile: dict[str, Any],
    melodic_style_profile: dict[str, Any],
    phrase_length_measures: int,
    rng: Any,
) -> dict[str, Any]:
    """Plan a measure-level register and tension contour for one phrase."""

    family = _style_family(style_profile, melodic_style_profile)
    role = str(phrase_role or "antecedent")
    length = max(1, int(phrase_length_measures or 4))
    contour_type = _contour_type(family, role, rng)
    register_points = _register_points(contour_type, length)
    tension_curve = _tension_curve(contour_type, role, length)
    return {
        "engine": "phrase_contour_v0962",
        "phrase_role": role,
        "style_family": family,
        "contour_type": contour_type,
        "register_points": register_points,
        "climax_position": _climax_position(register_points),
        "cadence_direction": _cadence_direction(contour_type, role),
        "tension_curve": tension_curve,
        "release_points": [index + 1 for index, value in enumerate(tension_curve) if value <= 0.35 or index == length - 1],
    }


def score_phrase_contour(melody_events: list[dict[str, Any]], contour: dict[str, Any]) -> dict[str, float]:
    """Score whether actual melody roughly follows the planned contour."""

    by_measure: dict[int, list[int]] = {}
    for event in melody_events:
        if event.get("type") == "rest":
            continue
        midi = event.get("midi")
        if midi is None:
            continue
        by_measure.setdefault(int(event.get("measure", 1) or 1), []).append(int(midi))
    actual = [sum(values) / len(values) for _, values in sorted(by_measure.items()) if values]
    planned = [float(item) for item in contour.get("register_points", [])]
    if len(actual) < 2 or len(planned) < 2:
        return {"phrase_contour_score": 0.0}
    actual_steps = _directions(actual)
    planned_steps = _directions(planned[: len(actual)])
    matches = sum(1 for a, b in zip(actual_steps, planned_steps, strict=False) if a == b or b == 0)
    return {"phrase_contour_score": round(matches / max(1, len(planned_steps)), 4)}


def _contour_type(family: str, role: str, rng: Any) -> str:
    if family == "jazz":
        return "jazz_guided_line"
    if family == "pop":
        return "pop_hook_curve"
    if family == "classical":
        return "falling_answer" if role in {"consequent", "final"} else "classical_periodic_balance"
    if family == "romantic":
        return "long_romantic_arc"
    if family == "chinese":
        return "pentatonic_open_space"
    if family == "cyberpunk":
        return "cyberpunk_cell_tension"
    choices = ["arch", "wave", "rising_question", "falling_answer"]
    if hasattr(rng, "choice"):
        return rng.choice(choices)
    return "arch"


def _register_points(contour_type: str, length: int) -> list[int]:
    templates = {
        "arch": [0, 3, 7, 2],
        "inverted_arch": [4, 0, -2, 3],
        "rising_question": [0, 2, 5, 7],
        "falling_answer": [5, 4, 2, 0],
        "wave": [0, 4, 2, 5],
        "terrace": [0, 0, 5, 5],
        "long_romantic_arc": [0, 3, 7, 9, 7, 4, 2, 0],
        "pentatonic_open_space": [0, 5, 2, 7],
        "jazz_guided_line": [2, 3, 5, 4],
        "cyberpunk_cell_tension": [0, 0, 3, 1],
        "pop_hook_curve": [0, 4, 4, 2],
        "classical_periodic_balance": [0, 2, 5, 0],
    }
    points = list(templates.get(contour_type, templates["arch"]))
    while len(points) < length:
        points.extend(points)
    return points[:length]


def _tension_curve(contour_type: str, role: str, length: int) -> list[float]:
    if role in {"consequent", "final", "cadence"}:
        base = [0.55, 0.75, 0.5, 0.2]
    elif contour_type == "cyberpunk_cell_tension":
        base = [0.45, 0.65, 0.75, 0.55]
    elif contour_type == "long_romantic_arc":
        base = [0.25, 0.45, 0.7, 0.85, 0.65, 0.45, 0.3, 0.2]
    else:
        base = [0.25, 0.45, 0.7, 0.35]
    while len(base) < length:
        base.extend(base)
    return [round(float(item), 3) for item in base[:length]]


def _climax_position(register_points: list[int]) -> float:
    if not register_points:
        return 0.5
    index = max(range(len(register_points)), key=lambda item: register_points[item])
    return round((index + 0.5) / max(1, len(register_points)), 3)


def _cadence_direction(contour_type: str, role: str) -> str:
    if role in {"consequent", "final", "cadence"}:
        return "down"
    if contour_type in {"rising_question", "cyberpunk_cell_tension"}:
        return "up"
    return "stable"


def _directions(values: list[float]) -> list[int]:
    directions = []
    for index in range(len(values) - 1):
        diff = values[index + 1] - values[index]
        directions.append(1 if diff > 0.1 else -1 if diff < -0.1 else 0)
    return directions


def _style_family(style_profile: dict[str, Any], melodic_style_profile: dict[str, Any]) -> str:
    tags = {str(item).lower() for item in (style_profile or {}).get("custom_style_tags", [])}
    family = str((melodic_style_profile or {}).get("style_family") or (style_profile or {}).get("base_style") or (style_profile or {}).get("style") or "classical").lower()
    if "cyberpunk" in tags or family == "electronic":
        return "cyberpunk"
    return family

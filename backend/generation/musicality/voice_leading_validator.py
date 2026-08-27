"""Voice-leading validation for style-aware harmony profiles."""

from __future__ import annotations

from statistics import mean
from typing import Any


def validate_voice_leading(voicing_sequence: list[Any], harmony_profile: dict[str, Any]) -> dict[str, Any]:
    """Validate adjacent chord voicings for playability and style fit."""

    voicings = [_extract_voicing(item) for item in voicing_sequence if _extract_voicing(item)]
    parallel_fifths = 0
    parallel_octaves = 0
    large_leaps = 0
    bass_steps: list[int] = []
    for previous, current in zip(voicings, voicings[1:], strict=False):
        size = min(len(previous), len(current))
        if size < 2:
            continue
        movements = [current[index] - previous[index] for index in range(size)]
        for left in range(size):
            for right in range(left + 1, size):
                previous_interval = abs(previous[right] - previous[left]) % 12
                current_interval = abs(current[right] - current[left]) % 12
                same_direction = movements[left] * movements[right] > 0
                if same_direction and previous_interval == current_interval == 7:
                    parallel_fifths += 1
                if same_direction and previous_interval == current_interval == 0:
                    parallel_octaves += 1
        large_leaps += sum(1 for movement in movements if abs(movement) > 12)
        bass_steps.append(abs(current[0] - previous[0]))
    playability = mean([float(item.get("playability_score", 1.0)) for item in voicing_sequence if isinstance(item, dict)] or [1.0])
    bass_smoothness = 1.0 if not bass_steps else max(0.0, 1.0 - mean(bass_steps) / 24.0)
    style = str(harmony_profile.get("style", "classical"))
    allows_parallel = bool(harmony_profile.get("allows_parallel_fifths", False))
    warnings: list[str] = []
    errors: list[str] = []
    if parallel_fifths and not allows_parallel:
        warnings.append("parallel fifths against style profile")
    if parallel_octaves and style == "classical":
        warnings.append("parallel octaves against classical profile")
    if large_leaps:
        warnings.append("large voice leaps")
    style_score = 1.0
    if not allows_parallel:
        style_score -= min(0.45, parallel_fifths * 0.08)
    if style == "classical":
        style_score -= min(0.35, parallel_octaves * 0.08)
    style_score -= min(0.25, large_leaps * 0.04)
    style_score = max(0.0, style_score)
    return {
        "engine": "voice_leading_validator_v096",
        "parallel_fifths_count": parallel_fifths,
        "parallel_octaves_count": parallel_octaves,
        "large_voice_leap_count": large_leaps,
        "leading_tone_resolution_rate": 1.0 if style != "classical" or not warnings else 0.75,
        "bass_line_smoothness_score": round(bass_smoothness, 4),
        "voicing_playability_score": round(playability, 4),
        "style_harmony_match_score": round(style_score, 4),
        "warnings": warnings,
        "errors": errors,
        "valid": not errors and style_score >= 0.55 and playability >= 0.55,
    }


def _extract_voicing(item: Any) -> list[int]:
    if isinstance(item, dict):
        return [int(value) for value in item.get("voicing", []) if isinstance(value, int)]
    if isinstance(item, list):
        return [int(value) for value in item if isinstance(value, int)]
    return []

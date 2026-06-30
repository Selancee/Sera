"""Musicality proxy metrics for Sera V0.5."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evaluation.analysis.music_statistics import analyze_musicxml, read_musicxml_text


def musicality_metrics_from_musicxml(musicxml: str) -> dict[str, float]:
    """Return stable V0.5 musicality proxy scores in the 0..1 range."""

    analysis = analyze_musicxml(musicxml)
    rhythm = analysis["rhythm_distribution"]
    intervals = analysis["pitch_interval_distribution"]
    complexity = analysis["rhythm_complexity"]
    phrase = analysis["phrase_metrics"]
    rhythmic_diversity = min(1.0, float(complexity.get("unique_duration_count", 0)) / 5.0)
    quarter_dominance = float(rhythm.get("quarter_note_ratio", 0.0))
    interval_variety = min(
        1.0,
        sum(
            1
            for key in [
                "same_pitch_ratio",
                "stepwise_second_ratio",
                "third_leap_ratio",
                "fourth_plus_leap_ratio",
            ]
            if float(intervals.get(key, 0.0)) > 0.05
        )
        / 4.0,
    )
    stepwise_penalty = min(1.0, max(0.0, float(intervals.get("stepwise_second_ratio", 0.0)) - 0.55) / 0.45)
    pitch_range = _pitch_range_score(analysis)
    motif = _bell(float(phrase.get("motif_recurrence_ratio", 0.0)), center=0.24, width=0.34)
    cadence = min(1.0, float(phrase.get("cadence_like_ending_ratio", 0.0)) * 1.4)
    phrase_contrast = _phrase_contrast_score(analysis)
    overall = (
        rhythmic_diversity * 0.18
        + (1.0 - quarter_dominance) * 0.14
        + interval_variety * 0.18
        + (1.0 - stepwise_penalty) * 0.12
        + pitch_range * 0.12
        + motif * 0.1
        + cadence * 0.1
        + phrase_contrast * 0.06
    )
    return {
        "rhythmic_diversity_score": round(rhythmic_diversity, 4),
        "quarter_note_dominance_score": round(quarter_dominance, 4),
        "melodic_interval_variety_score": round(interval_variety, 4),
        "stepwise_overuse_penalty": round(stepwise_penalty, 4),
        "pitch_range_score": round(pitch_range, 4),
        "motif_recurrence_score": round(motif, 4),
        "cadence_presence_score": round(cadence, 4),
        "phrase_contrast_score": round(phrase_contrast, 4),
        "overall_musicality_proxy_score": round(max(0.0, min(1.0, overall)), 4),
    }


def musicality_metrics_from_file(path: str | Path) -> dict[str, float]:
    """Return musicality metrics for one MusicXML file."""

    return musicality_metrics_from_musicxml(read_musicxml_text(path))


def _pitch_range_score(analysis: dict[str, Any]) -> float:
    max_leap = float(analysis["pitch_interval_distribution"].get("max_leap", 0.0))
    if max_leap <= 0:
        return 0.0
    if 7 <= max_leap <= 19:
        return 1.0
    if max_leap < 7:
        return max_leap / 7.0
    return max(0.0, 1.0 - (max_leap - 19) / 24.0)


def _phrase_contrast_score(analysis: dict[str, Any]) -> float:
    contour = analysis.get("melody_contour", "static")
    entropy = float(analysis["rhythm_complexity"].get("rhythmic_entropy", 0.0))
    contour_bonus = 0.25 if contour in {"arch", "wave"} else 0.1 if contour in {"ascending", "descending"} else 0.0
    return max(0.0, min(1.0, contour_bonus + min(0.75, entropy / 3.0)))


def _bell(value: float, center: float, width: float) -> float:
    return max(0.0, 1.0 - abs(value - center) / max(0.001, width))

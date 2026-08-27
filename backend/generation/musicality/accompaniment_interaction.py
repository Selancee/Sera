"""Accompaniment and melody interaction summary for V0.96.2."""

from __future__ import annotations

from typing import Any


def plan_accompaniment_interaction(
    melody_phrase: dict[str, Any],
    harmony_plan: list[Any],
    style_profile: dict[str, Any],
    accompaniment_profile: dict[str, Any],
    rng: Any,
) -> dict[str, Any]:
    """Describe how the existing accompaniment should support the phrase."""

    family = str((style_profile or {}).get("style_family") or (style_profile or {}).get("base_style") or (style_profile or {}).get("style") or "classical").lower()
    tags = {str(item).lower() for item in (style_profile or {}).get("custom_style_tags", [])}
    if "cyberpunk" in tags or family == "electronic":
        family = "cyberpunk"
    interaction = {
        "jazz": "supportive_pulse",
        "pop": "supportive_pulse",
        "classical": "cadence_support",
        "romantic": "gap_filling_inner_voice",
        "chinese": "pedal_tension",
        "cyberpunk": "pedal_tension",
    }.get(family, "supportive_pulse")
    measures = list((melody_phrase or {}).get("measures") or [])
    phrase_end_count = sum(1 for item in measures if item.get("phrase_end"))
    accompaniment_style = str((accompaniment_profile or {}).get("style") or "")
    call_response = 1 if interaction in {"call_response", "rhythmic_answer"} else 0
    if family in {"jazz", "pop"} and accompaniment_style in {"bass_chord", "syncopated", "arpeggiated_chords"}:
        call_response = max(call_response, phrase_end_count)
    return {
        "engine": "accompaniment_interaction_v0962",
        "interaction_type": interaction,
        "melody_supported": bool(measures),
        "cadence_supported": phrase_end_count > 0 or interaction == "cadence_support",
        "call_response_events": call_response,
        "counterline_score": 0.65 if interaction in {"bass_counterline", "gap_filling_inner_voice"} else 0.35,
        "accompaniment_style": accompaniment_style,
        "warnings": [],
    }

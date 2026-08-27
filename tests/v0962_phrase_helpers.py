from __future__ import annotations

from typing import Any

from backend.generation.musicality.melodic_style_engine import build_melodic_style_profile
from backend.generation.musicality.phrase_melody_engine import generate_period_melody
from backend.generation.seed_service import make_seeded_rng


def period_for_style(style: str, seed: int = 9602) -> dict[str, Any]:
    key = {
        "jazz": "F major",
        "chinese": "D major",
        "cyberpunk": "A minor",
    }.get(style, "C major")
    mode = "minor" if "minor" in key.lower() else "major"
    style_profile = _style_profile(style, key)
    melodic = build_melodic_style_profile(style_profile, key, mode, "intermediate")
    harmony = _harmony_for_style(style)
    rhythm = [_rhythm_measure(number) for number in range(1, 9)]
    return generate_period_melody(
        {
            "key": key,
            "mode": mode,
            "length_measures": 8,
            "phrase_length_measures": 4,
            "measures": [{"measure": number, "section": "A" if number <= 4 else "B"} for number in range(1, 9)],
        },
        harmony,
        rhythm,
        style_profile,
        melodic,
        {},
        make_seeded_rng(seed, f"test:v0962:{style}"),
    )


def _style_profile(style: str, key: str) -> dict[str, Any]:
    if style == "cyberpunk":
        return {
            "style": "custom",
            "base_style": "electronic",
            "custom_style_tags": ["cyberpunk"],
            "texture": "ostinato",
            "harmony_flavor": "minor_modal",
            "key": key,
        }
    return {
        "style": style,
        "base_style": style,
        "custom_style_tags": [style] if style == "chinese" else [],
        "key": key,
    }


def _harmony_for_style(style: str) -> list[str]:
    if style == "jazz":
        return ["ii7", "V7", "Imaj7", "VI7", "ii7", "V7", "Imaj7", "Imaj7"]
    if style == "chinese":
        return ["I", "IV(add2)", "V5", "I", "I", "IV(add2)", "V5", "I"]
    if style == "cyberpunk":
        return ["i", "VII", "VI", "VII", "i", "VII", "V", "i"]
    if style == "pop":
        return ["I", "V", "vi", "IV", "I", "V", "vi", "IV"]
    return ["I", "IV", "V", "I", "ii", "V", "I", "I"]


def _rhythm_measure(number: int) -> dict[str, Any]:
    patterns = [
        [
            {"duration_quarters": 0.5, "offset_quarters": 0.0},
            {"duration_quarters": 0.5, "offset_quarters": 0.5},
            {"duration_quarters": 1.0, "offset_quarters": 1.0},
            {"duration_quarters": 1.0, "offset_quarters": 2.0},
            {"duration_quarters": 1.0, "offset_quarters": 3.0},
        ],
        [
            {"duration_quarters": 1.0, "offset_quarters": 0.0},
            {"duration_quarters": 1.0, "offset_quarters": 1.0},
            {"duration_quarters": 0.5, "offset_quarters": 2.0},
            {"duration_quarters": 0.5, "offset_quarters": 2.5},
            {"duration_quarters": 1.0, "offset_quarters": 3.0},
        ],
        [
            {"duration_quarters": 1.5, "offset_quarters": 0.0},
            {"duration_quarters": 0.5, "offset_quarters": 1.5},
            {"duration_quarters": 1.0, "offset_quarters": 2.0},
            {"duration_quarters": 1.0, "offset_quarters": 3.0},
        ],
        [
            {"duration_quarters": 2.0, "offset_quarters": 0.0},
            {"duration_quarters": 1.0, "offset_quarters": 2.0},
            {"duration_quarters": 1.0, "offset_quarters": 3.0},
        ],
    ]
    return {"measure": number, "events": patterns[(number - 1) % len(patterns)]}

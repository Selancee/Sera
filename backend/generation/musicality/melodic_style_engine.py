"""Style-aware melodic material for V0.94 generation."""

from __future__ import annotations

import random
from typing import Any


DEGREE_TO_OFFSET = {
    "1": 0,
    "b2": 1,
    "2": 2,
    "b3": 3,
    "3": 4,
    "4": 5,
    "#4": 6,
    "b5": 6,
    "5": 7,
    "b6": 8,
    "6": 9,
    "b7": 10,
    "7": 11,
}
OFFSET_TO_DEGREE = {value: key for key, value in DEGREE_TO_OFFSET.items() if key not in {"#4", "b5"}}


def build_melodic_style_profile(style_profile: dict[str, Any], key: str, mode: str, difficulty: str) -> dict[str, Any]:
    """Return executable melodic controls derived from the custom style profile."""

    style_profile = dict(style_profile or {})
    tags = {str(tag).lower() for tag in style_profile.get("custom_style_tags", [])}
    base_style = str(style_profile.get("base_style") or "").lower()
    texture = str(style_profile.get("texture") or "").lower()
    harmony = str(style_profile.get("harmony_flavor") or "").lower()
    family = _style_family(base_style, tags, texture, harmony)
    profiles = {
        "jazz": {
            "pitch_vocabulary": "jazz_chord_tones_extensions_chromatic_approach",
            "degree_vocabulary": ["1", "b2", "2", "3", "5", "6", "b7", "7"],
            "contour_policy": "motivic_with_chromatic_approach",
            "interval_policy": "small_steps_with_guided_chromaticism",
            "motif_length": 4,
            "register_bias": "middle",
            "allow_color_tones": True,
            "target_tones": ["3rd", "7th", "9th", "13th"],
            "avoid_unresolved_tritone": False,
            "requires_resolution": True,
        },
        "pop": {
            "pitch_vocabulary": "major_minor_pentatonic_hook",
            "degree_vocabulary": ["1", "2", "3", "5", "6"],
            "contour_policy": "hook_based_repetition_with_variation",
            "interval_policy": "mostly_stepwise_with_memorable_leaps",
            "motif_length": 3,
            "register_bias": "middle_high",
            "allow_color_tones": True,
            "target_tones": ["1", "3", "5", "6"],
            "avoid_unresolved_tritone": True,
        },
        "classical": {
            "pitch_vocabulary": "functional_diatonic_with_leading_tone",
            "degree_vocabulary": ["1", "2", "3", "4", "5", "6", "7"],
            "contour_policy": "balanced_periodic_phrase",
            "interval_policy": "stepwise_with_controlled_arpeggiation",
            "motif_length": 4,
            "register_bias": "middle",
            "allow_color_tones": False,
            "target_tones": ["1", "3", "5", "leading_tone_resolution"],
            "avoid_unresolved_tritone": True,
        },
        "cyberpunk": {
            "pitch_vocabulary": "minor_modal_with_limited_chromatic",
            "degree_vocabulary": ["1", "2", "b3", "4", "5", "b6", "b7"],
            "contour_policy": "short_cell_repetition",
            "interval_policy": "small_steps_with_controlled_tension",
            "motif_length": 3,
            "register_bias": "middle_low",
            "allow_color_tones": True,
            "avoid_unresolved_tritone": True,
        },
        "anime": {
            "pitch_vocabulary": "major_minor_mixed",
            "degree_vocabulary": ["1", "2", "3", "4", "5", "6", "7"],
            "contour_policy": "lyrical_arch",
            "interval_policy": "stepwise_with_expressive_sixth",
            "motif_length": 4,
            "register_bias": "middle_high",
            "allow_color_tones": True,
            "avoid_unresolved_tritone": True,
        },
        "chinese": {
            "pitch_vocabulary": "pentatonic",
            "degree_vocabulary": ["1", "2", "3", "5", "6"],
            "contour_policy": "modal_wave",
            "interval_policy": "pentatonic_steps_and_open_fifths",
            "motif_length": 4,
            "register_bias": "middle",
            "allow_color_tones": False,
            "avoid_unresolved_tritone": True,
        },
        "romantic": {
            "pitch_vocabulary": "tonal_with_neighbor_tones",
            "degree_vocabulary": ["1", "2", "3", "4", "5", "6", "7"],
            "contour_policy": "long_arch",
            "interval_policy": "expressive_leaps_resolved",
            "motif_length": 5,
            "register_bias": "middle_high",
            "allow_color_tones": True,
            "avoid_unresolved_tritone": True,
        },
        "default": {
            "pitch_vocabulary": "diatonic",
            "degree_vocabulary": ["1", "2", "3", "4", "5", "6", "7"] if mode != "minor" else ["1", "2", "b3", "4", "5", "b6", "7"],
            "contour_policy": "balanced",
            "interval_policy": "mostly_stepwise",
            "motif_length": 4,
            "register_bias": "middle",
            "allow_color_tones": False,
            "avoid_unresolved_tritone": True,
        },
    }
    profile = dict(profiles.get(family, profiles["default"]))
    profile.update(
        {
            "style_family": family,
            "key": key,
            "mode": mode,
            "difficulty": difficulty,
            "source_style_profile": style_profile,
            "source_prompt_terms": list(style_profile.get("source_prompt_terms", [])),
        }
    )
    if difficulty == "beginner":
        profile["allow_color_tones"] = False
        profile["motif_length"] = min(int(profile["motif_length"]), 4)
    return profile


def generate_style_motif(profile: dict[str, Any], phrase_role: str, rng: random.Random) -> list[int]:
    labels = generate_phrase_degree_labels(profile, phrase_role, int(profile.get("motif_length", 4)), rng)
    return [DEGREE_TO_OFFSET.get(label, 0) for label in labels]


def generate_phrase_degrees(profile: dict[str, Any], phrase_role: str, length: int, rng: random.Random) -> list[int]:
    labels = generate_phrase_degree_labels(profile, phrase_role, length, rng)
    return [DEGREE_TO_OFFSET.get(label, 0) for label in labels]


def apply_style_contour(degrees: list[int], profile: dict[str, Any], phrase_role: str, rng: random.Random) -> list[int]:
    labels = [OFFSET_TO_DEGREE.get(int(degree) % 12, "1") for degree in degrees]
    contoured = _apply_label_contour(labels, profile, phrase_role, rng)
    return [DEGREE_TO_OFFSET.get(label, 0) for label in contoured]


def generate_phrase_degree_labels(profile: dict[str, Any], phrase_role: str, length: int, rng: random.Random) -> list[str]:
    family = str(profile.get("style_family", "default"))
    if family == "cyberpunk":
        cells = [["1", "b3", "2"], ["5", "b3", "2"], ["1", "5", "b3"], ["b7", "5", "b3"]]
        labels = _repeat_cell(rng.choice(cells), length)
        if length >= 5 and rng.random() < 0.45:
            labels[-2] = "b6"
        return _cadence_adjust(labels, phrase_role, ["b7", "1"])
    if family == "anime":
        cells = [["1", "6", "5", "3"], ["5", "3", "2", "1"], ["1", "3", "5", "6"]]
        labels = _repeat_cell(rng.choice(cells), length)
        return _apply_label_contour(_cadence_adjust(labels, phrase_role, ["2", "1"]), profile, phrase_role, rng)
    if family == "chinese":
        cells = [["1", "2", "3", "5"], ["5", "6", "5", "3"], ["1", "5", "6", "3"]]
        labels = _repeat_cell(rng.choice(cells), length)
        return _cadence_adjust(labels, phrase_role, ["5", "1"])
    if family == "romantic":
        cells = [["1", "2", "3", "5", "6"], ["3", "4", "5", "6", "5"], ["1", "3", "2", "4", "5"]]
        labels = _repeat_cell(rng.choice(cells), length)
        return _apply_label_contour(_cadence_adjust(labels, phrase_role, ["7", "1"]), profile, phrase_role, rng)
    if family == "jazz":
        cells = [["3", "b3", "2", "3"], ["7", "b7", "6", "5"], ["2", "3", "5", "b7"], ["5", "6", "b7", "7"]]
        labels = _repeat_cell(rng.choice(cells), length)
        return _cadence_adjust(labels, phrase_role, ["b7", "3"] if phrase_role != "final" else ["7", "1"])
    if family == "pop":
        cells = [["1", "3", "5"], ["5", "6", "5"], ["3", "2", "1"], ["1", "5", "6"]]
        labels = _repeat_cell(rng.choice(cells), length)
        if length >= 4 and phrase_role == "contrast":
            labels[1] = "6"
        return _cadence_adjust(labels, phrase_role, ["5", "1"])
    if family == "classical":
        cells = [["1", "2", "3", "5"], ["3", "4", "5", "7"], ["5", "4", "3", "2"]]
        labels = _repeat_cell(rng.choice(cells), length)
        return _apply_label_contour(_cadence_adjust(labels, phrase_role, ["7", "1"]), profile, phrase_role, rng)
    vocabulary = list(profile.get("degree_vocabulary") or ["1", "2", "3", "5"])
    labels = _repeat_cell(vocabulary[:4], length)
    return _cadence_adjust(labels, phrase_role, ["5", "1"])


def _style_family(base_style: str, tags: set[str], texture: str, harmony: str) -> str:
    if "cyberpunk" in tags or base_style == "electronic" or "minor_modal" in harmony or texture == "ostinato":
        return "cyberpunk"
    if "anime" in tags:
        return "anime"
    if "chinese" in tags or "pentatonic" in tags or base_style == "chinese" or "pentatonic" in harmony:
        return "chinese"
    if base_style == "romantic" or "nocturne" in tags:
        return "romantic"
    if base_style == "jazz" or "jazz" in tags:
        return "jazz"
    if base_style == "pop" or "pop" in tags:
        return "pop"
    if base_style == "classical" or "classical" in tags:
        return "classical"
    return "default"


def _repeat_cell(cell: list[str], length: int) -> list[str]:
    out: list[str] = []
    while len(out) < max(1, length):
        out.extend(cell)
    return out[: max(1, length)]


def _cadence_adjust(labels: list[str], phrase_role: str, ending: list[str]) -> list[str]:
    if phrase_role in {"cadence", "final"} and len(labels) >= 2:
        labels[-2:] = ending[-2:]
    return labels


def _apply_label_contour(labels: list[str], profile: dict[str, Any], phrase_role: str, rng: random.Random) -> list[str]:
    policy = str(profile.get("contour_policy", "balanced"))
    if len(labels) < 4 or phrase_role in {"cadence", "final"}:
        return labels
    if policy == "lyrical_arch":
        arch = ["1", "3", "5", "6", "5", "3", "2", "1"]
        return _repeat_cell(arch if rng.random() < 0.5 else ["5", "6", "7", "6", "5", "3", "2", "1"], len(labels))
    if policy == "long_arch":
        return _repeat_cell(["1", "2", "3", "5", "6", "5", "4", "3"], len(labels))
    if policy == "modal_wave":
        return _repeat_cell(["1", "2", "3", "5", "3", "2", "6", "5"], len(labels))
    return labels

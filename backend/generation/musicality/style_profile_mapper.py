"""Map custom prompt style words to executable V0.92 musical controls."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.services.prompt_term_extractor import extract_prompt_terms


STYLE_MAPPINGS: dict[str, dict[str, Any]] = {
    "cyberpunk": {
        "base_style": "electronic",
        "custom_style_tags": ["cyberpunk", "mechanical", "cold", "futuristic"],
        "rhythmic_density": "medium_high",
        "syncopation": "medium_high",
        "texture": "ostinato",
        "accompaniment_style": "repeating_bass",
        "harmony_flavor": "minor_modal",
        "dynamic_contrast": "high",
        "cadence_strength": "medium",
        "register_bias": "middle_low",
        "timbre_hint": "synth_like_piano",
        "left_hand_pattern": "ostinato_repeating_bass",
    },
    "anime": {
        "base_style": "pop",
        "custom_style_tags": ["anime", "lyrical", "bright"],
        "rhythmic_density": "medium",
        "texture": "melody_accompaniment",
        "accompaniment_style": "arpeggiated_chords",
        "harmony_flavor": "major_minor_mixed",
        "dynamic_contrast": "medium",
        "cadence_strength": "strong",
    },
    "cinematic": {
        "base_style": "cinematic",
        "custom_style_tags": ["cinematic", "dramatic"],
        "rhythmic_density": "medium",
        "texture": "chordal_arpeggiated",
        "accompaniment_style": "bass_chord",
        "harmony_flavor": "minor_epic",
        "dynamic_contrast": "high",
        "cadence_strength": "strong",
    },
    "new_age": {
        "base_style": "new_age",
        "custom_style_tags": ["new_age", "ambient", "gentle"],
        "rhythmic_density": "low_medium",
        "texture": "arpeggiated",
        "accompaniment_style": "flowing_arpeggio",
        "harmony_flavor": "modal_soft",
        "dynamic_contrast": "low",
        "cadence_strength": "soft",
    },
    "game": {
        "base_style": "game",
        "custom_style_tags": ["game", "loopable", "theme"],
        "rhythmic_density": "medium",
        "texture": "ostinato_melody",
        "accompaniment_style": "repeating_pattern",
        "harmony_flavor": "modal_loop",
        "dynamic_contrast": "medium",
        "cadence_strength": "loopable",
    },
    "chinese": {
        "base_style": "chinese",
        "custom_style_tags": ["chinese", "pentatonic", "modal"],
        "rhythmic_density": "medium",
        "texture": "pentatonic_open_texture",
        "accompaniment_style": "open_fifth_pedal",
        "harmony_flavor": "pentatonic_modal",
        "dynamic_contrast": "medium",
        "cadence_strength": "modal",
    },
}

GENERIC_CUSTOM_PROFILE = {
    "base_style": "custom",
    "custom_style_tags": ["unknown"],
    "rhythmic_density": "medium",
    "texture": "melody_accompaniment",
    "accompaniment_style": "bass_chord",
    "harmony_flavor": "diatonic",
    "dynamic_contrast": "medium",
    "cadence_strength": "medium",
}

ALLOWED_GENERATION_ENGINES = [
    "rhythm_engine",
    "texture_engine",
    "accompaniment_engine",
    "harmony_engine",
    "cadence_engine",
    "dynamics_engine",
]


def map_style_profile(prompt: str, detected_style: str = "classical") -> dict[str, Any]:
    """Return a custom style mapping, or an empty mapping for normal styles."""

    text = str(prompt or "").replace("-", " ").replace("_", " ").lower()
    terms_payload = extract_prompt_terms(prompt)
    normalized_terms = {str(term.get("normalized", "")) for term in terms_payload.get("prompt_terms", [])}
    profile: dict[str, Any] | None = None
    if "cyberpunk" in normalized_terms or "dark_electronic" in normalized_terms or "cyberpunk" in text or ("sci fi" in text and "dark" in text):
        profile = deepcopy(STYLE_MAPPINGS["cyberpunk"])
    elif "anime" in normalized_terms or "anime" in text or "animation theme" in text:
        profile = deepcopy(STYLE_MAPPINGS["anime"])
    elif "cinematic" in normalized_terms or "cinematic" in text or "trailer" in text:
        profile = deepcopy(STYLE_MAPPINGS["cinematic"])
    elif "new_age" in normalized_terms or "ambient" in normalized_terms or "new age" in text or ("ambient" in text and "piano" in text):
        profile = deepcopy(STYLE_MAPPINGS["new_age"])
    elif "game" in normalized_terms or "game soundtrack" in text or "video game" in text or "game theme" in text:
        profile = deepcopy(STYLE_MAPPINGS["game"])
    elif detected_style == "chinese" or bool({"chinese", "pentatonic", "wuxia", "xianxia"} & normalized_terms):
        profile = deepcopy(STYLE_MAPPINGS["chinese"])
    elif detected_style not in {"classical", "romantic", "jazz", "pop", "electronic", "chinese", "experimental", "ambient", "minimalist"}:
        profile = deepcopy(GENERIC_CUSTOM_PROFILE)

    if not profile:
        return {}

    tags = list(dict.fromkeys(str(tag) for tag in profile.get("custom_style_tags", [])))
    if "dark" in text and "dark" not in tags:
        tags.append("dark")
    if "mechanical" in normalized_terms and "mechanical" not in tags:
        tags.append("mechanical")
    if "cold" in normalized_terms and "cold" not in tags:
        tags.append("cold")
    if "futuristic" in normalized_terms and "futuristic" not in tags:
        tags.append("futuristic")
    if "gentle" in text and "gentle" not in tags:
        tags.append("gentle")
    profile["custom_style_tags"] = tags or ["unknown"]
    profile["source_prompt_terms"] = list(terms_payload.get("source_prompt_terms", []))
    profile["prompt_terms"] = list(terms_payload.get("prompt_terms", []))
    profile["allowed_generation_engines"] = list(ALLOWED_GENERATION_ENGINES)
    return {
        "style": "custom",
        "base_style": str(profile.get("base_style", detected_style or "custom")),
        "custom_style_tags": profile["custom_style_tags"],
        "style_profile": profile,
    }

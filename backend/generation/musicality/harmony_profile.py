"""Style-aware harmony profile selection for V0.96."""

from __future__ import annotations

from typing import Any

from backend.generation.musicality.variation import variation_offset


STYLE_PROFILES: dict[str, dict[str, Any]] = {
    "jazz": {
        "vocabulary": ["ii7", "V7alt", "Imaj9", "VI7b9", "tritone_sub", "rootless_9th", "13th"],
        "progressions": [["ii7", "V7", "Imaj7", "VI7"], ["ii7", "bII7", "Imaj9", "VI7alt"]],
        "voicing_style": "rootless_extended",
        "allows_extensions": True,
        "allows_parallel_fifths": False,
    },
    "chinese": {
        "vocabulary": ["pentatonic_verticalization", "open_fifth", "quartal", "pedal_tone", "gong_shang_jue_zhi_yu"],
        "progressions": [["I5", "V5", "I5", "V5"], ["I", "IV(add2)", "V5", "I"]],
        "voicing_style": "open_fifth_quartal",
        "allows_extensions": False,
        "allows_parallel_fifths": True,
    },
    "classical": {
        "vocabulary": ["I", "IV", "V", "I", "ii6", "V7", "leading_tone_resolution"],
        "progressions": [["I", "IV", "V", "I"], ["I", "ii", "V", "I"]],
        "voicing_style": "closed_four_part",
        "allows_extensions": False,
        "allows_parallel_fifths": False,
    },
    "pop": {
        "vocabulary": ["I", "V", "vi", "IV", "sus4", "add9", "slash_chord"],
        "progressions": [["I", "V", "vi", "IV"], ["vi", "IV", "I", "V"], ["I", "vi", "IV", "V"]],
        "voicing_style": "playable_piano_pop",
        "allows_extensions": True,
        "allows_parallel_fifths": True,
    },
    "romantic": {
        "vocabulary": ["secondary_dominant", "extended_dominant", "passing_dim7", "chromatic_bass", "cadential_64"],
        "progressions": [["I", "vi", "ii", "V7"], ["I", "V/V", "V7", "I"], ["i", "iv", "V7", "i"]],
        "voicing_style": "wide_arpeggiated",
        "allows_extensions": True,
        "allows_parallel_fifths": False,
    },
    "electronic": {
        "vocabulary": ["minor_modal", "pedal_point", "ostinato_bass", "quartal_cluster", "sus_cluster"],
        "progressions": [["i", "VII", "VI", "VII"], ["i", "iv(add4)", "VI", "V"], ["i", "i", "VII", "VI"]],
        "voicing_style": "modal_pedal_cluster",
        "allows_extensions": True,
        "allows_parallel_fifths": True,
    },
}


def build_harmony_profile(style_profile: dict[str, Any], key: str, mode: str, difficulty: str) -> dict[str, Any]:
    """Map a Sera style profile to harmonic vocabulary and constraints."""

    style = _style_key(style_profile)
    if style == "cyberpunk":
        style = "electronic"
    template = dict(STYLE_PROFILES.get(style, STYLE_PROFILES["classical"]))
    profile = {
        "engine": "harmony_profile_v096",
        "style": style,
        "key": key,
        "mode": mode,
        "difficulty": difficulty,
        **template,
    }
    if difficulty == "beginner":
        profile["progressions"] = [["I", "V", "I", "V"]] if mode == "major" else [["i", "V", "i", "V"]]
        profile["vocabulary"] = [item for item in profile["vocabulary"] if "alt" not in item and "13" not in item]
    elif mode == "minor":
        if style == "classical":
            profile["progressions"] = [["i", "iv", "V", "i"], ["i", "iv", "V7", "i"]]
        elif style == "romantic":
            profile["progressions"] = [["i", "iv", "V7", "i"], ["i", "V/V", "V7", "i"], ["i", "VI", "iv", "V7"]]
        elif style == "pop":
            profile["progressions"] = [["i", "VII", "VI", "VII"], ["i", "VI", "III", "VII"], ["i", "VI", "iv", "V"]]
        elif style == "jazz":
            profile["progressions"] = [["ii7", "V7", "i", "VI7"], ["ii7", "bII7", "i", "V7"]]
    return profile


def select_progression_from_profile(profile: dict[str, Any], length_measures: int, rng: Any) -> dict[str, Any]:
    """Pick and repeat a style profile progression to cover the target length."""

    progressions = list(profile.get("progressions") or [["I", "V", "I", "V"]])
    if progressions and ("variation_index" in profile or profile.get("variation_seed")):
        seed_text = str(profile.get("variation_seed", ""))
        offset = variation_offset(seed_text, len(progressions), "harmony_profile:progression") if seed_text else 0
        if seed_text:
            offset = (offset + sum(ord(char) for char in seed_text)) % len(progressions)
        index = (int(profile.get("variation_index", 0) or 0) + offset) % len(progressions)
    else:
        index = rng.randrange(len(progressions)) if hasattr(rng, "randrange") and progressions else 0
    cell = list(progressions[index])
    chords = [cell[position % len(cell)] for position in range(max(1, int(length_measures or 1)))]
    if len(chords) >= 2:
        style = str(profile.get("style") or "classical")
        if style == "jazz":
            chords[-2:] = ["V7", "Imaj7"]
        elif style == "chinese":
            chords[-2:] = ["V5", "I5"]
        elif style == "classical":
            chords[-2:] = ["V7", "I"]
        elif style == "pop":
            chords[-2:] = ["V", "I"]
        elif style == "romantic":
            chords[-2:] = ["V7", "I"] if profile.get("mode") != "minor" else ["V7", "i"]
        elif style == "electronic":
            chords[-2:] = ["VII", "i"] if profile.get("mode") == "minor" else ["VII", "I"]
        elif profile.get("mode") == "minor":
            chords[-2:] = ["V", "i"]
        else:
            chords[-2:] = ["V", "I"]
    return {
        "progression": cell,
        "chords": chords,
        "progression_source": f"{profile.get('style', 'classical')}_harmony_profile",
    }


def _style_key(style_profile: dict[str, Any]) -> str:
    tags = {str(item).lower() for item in style_profile.get("custom_style_tags", [])}
    raw_style = str(style_profile.get("style") or "").replace("-", "_").lower()
    raw_base = str(style_profile.get("base_style") or "").replace("-", "_").lower()
    style = raw_base if raw_style in {"", "custom"} else raw_style
    style = style or raw_base or "classical"
    if "cyberpunk" in tags:
        return "electronic"
    return style if style in STYLE_PROFILES else "classical"

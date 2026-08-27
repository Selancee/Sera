"""Harmony plans for V0.9 generation."""

from __future__ import annotations

from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.harmony_profile import build_harmony_profile, select_progression_from_profile
from backend.generation.musicality.variation import variation_offset
from backend.generation.seed_service import make_seeded_rng


PROGRESSIONS = {
    "pop": ["I", "V", "vi", "IV"],
    "classical": ["I", "IV", "V", "I"],
    "romantic": ["I", "vi", "IV", "V"],
    "jazz": ["ii", "V", "I", "vi"],
    "minor": ["i", "VI", "III", "VII"],
    "minor_functional": ["i", "iv", "V", "i"],
    "beginner": ["I", "V", "I", "V"],
    "chinese": ["I", "V", "I", "V"],
}


class HarmonyEngine:
    def generate(self, profile: GenerationProfile, measure_count: int) -> dict[str, object]:
        mode = "minor" if "minor" in profile.key.lower() else "major"
        harmony_profile = build_harmony_profile(
            {
                **dict(profile.style_profile or {}),
                "style": profile.style,
                "base_style": profile.base_style,
                "custom_style_tags": list(profile.custom_style_tags or []),
            },
            key=profile.key,
            mode=mode,
            difficulty=profile.difficulty,
        )
        harmony_profile["variation_index"] = profile.variation_index
        harmony_profile["variation_seed"] = profile.variation_seed
        profile_choice = select_progression_from_profile(
            harmony_profile,
            measure_count,
            make_seeded_rng(profile.run_seed or 1, f"harmony_profile:{profile.variation_seed or 'default'}"),
        )
        progression = list(profile_choice.get("progression") or self.progression_for_profile(profile))
        old_variation_override_used = False
        if not profile_choice.get("progression") and profile.variation_seed:
            variants = self.progression_variants_for_profile(profile, progression)
            progression = variants[variation_offset(profile.variation_seed, len(variants), "harmony:progression")]
            old_variation_override_used = True
        chords = list(profile_choice.get("chords") or [progression[(index - 1) % len(progression)] for index in range(1, measure_count + 1)])
        return {
            "engine": "harmony_engine_v09",
            "progression": progression,
            "chords": chords,
            "harmony_profile": harmony_profile,
            "progression_source": profile_choice.get("progression_source", "legacy_harmony_engine"),
            "harmony_progression_source": "harmony_profile" if profile_choice.get("progression") else "legacy_harmony_engine",
            "style_progression_family": harmony_profile.get("style", profile.style),
            "selected_progression": progression,
            "old_variation_override_used": old_variation_override_used,
            "variation_seed": profile.variation_seed,
            "style_parameters_applied": {"harmony_flavor": profile.harmony_flavor},
        }

    @staticmethod
    def progression_for_profile(profile: GenerationProfile) -> list[str]:
        if profile.harmony_flavor in {"minor_modal", "minor_epic"}:
            return PROGRESSIONS["minor"]
        if profile.harmony_flavor == "pentatonic_modal":
            return ["I", "V", "I", "V"]
        if profile.harmony_flavor in {"modal_loop", "modal_soft", "pentatonic_modal"}:
            return ["i", "VII", "VI", "VII"] if "minor" in profile.key.lower() else ["I", "VII", "IV", "VII"]
        style = profile.base_style if profile.style == "custom" else profile.style
        if style == "chinese":
            return PROGRESSIONS["chinese"]
        if profile.difficulty == "beginner":
            return PROGRESSIONS["beginner"]
        if "minor" in profile.key.lower():
            return PROGRESSIONS["minor_functional"] if style in {"classical", "romantic"} else PROGRESSIONS["minor"]
        return PROGRESSIONS.get(style, PROGRESSIONS["classical"])

    @staticmethod
    def progression_variants_for_profile(profile: GenerationProfile, default: list[str]) -> list[list[str]]:
        if profile.harmony_flavor in {"minor_modal", "minor_epic"} or "minor" in profile.key.lower():
            return [
                default,
                ["i", "iv", "V", "i"],
                ["i", "VI", "iv", "V"],
                ["i", "VII", "VI", "V"],
            ]
        style = profile.base_style if profile.style == "custom" else profile.style
        if style == "pop":
            return [default, ["I", "vi", "IV", "V"], ["I", "V", "IV", "V"], ["vi", "IV", "I", "V"]]
        if style in {"electronic", "game"}:
            return [default, ["I", "V", "vi", "IV"], ["I", "vi", "V", "IV"], ["I", "V", "IV", "V"]]
        if style == "jazz":
            return [default, ["I", "vi", "ii", "V"], ["ii", "V", "iii", "vi"], ["I", "IV", "iii", "vi"]]
        return [default, ["I", "V", "vi", "IV"], ["I", "vi", "IV", "V"], ["I", "ii", "V", "I"]]

"""Generation profile controls shared by V0.9 musicality engines."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from backend.generation.musicality.style_profile_mapper import map_style_profile
from backend.models.schemas import CompositionPlan


@dataclass(slots=True)
class GenerationProfile:
    style: str = "classical"
    base_style: str = "classical"
    custom_style_tags: list[str] | None = None
    style_profile: dict[str, Any] | None = None
    difficulty: str = "intermediate"
    meter: str = "4/4"
    key: str = "C major"
    length_measures: int = 16
    rhythmic_density: str = "medium"
    syncopation: str = "low"
    texture: str = "melody_accompaniment"
    accompaniment_style: str = "bass_chord"
    harmony_flavor: str = "diatonic"
    cadence_strength: str = "clear"
    dynamic_contrast: str = "medium"
    register_bias: str = "middle"
    timbre_hint: str = ""
    requires_accompaniment: bool = True
    requires_dotted_rhythm: bool = True
    requires_cadence: bool = True
    min_rhythmic_variety: int = 3
    min_pitch_range: int = 7
    max_consecutive_quarters: int = 3
    max_repeated_rhythm_measures: int = 2
    variation_seed: str = ""
    variation_index: int = 0
    run_seed: int = 0
    seed_source: str = ""
    variant_id: str = ""
    generation_nonce: str = ""

    @classmethod
    def from_plan(cls, plan: CompositionPlan) -> "GenerationProfile":
        intent = plan.intent
        prompt = str(intent.prompt or "").lower()
        mapped = dict(intent.style_profile or {})
        if not mapped and (intent.custom_style_tags or intent.style == "custom"):
            mapped = dict(map_style_profile(prompt, intent.base_style or intent.style).get("style_profile") or {})
        base_style = str(mapped.get("base_style") or intent.base_style or intent.style or "classical")
        tags = [str(item) for item in (intent.custom_style_tags or mapped.get("custom_style_tags") or [])]
        profile = cls(
            style=_safe_choice(intent.style, {"classical", "romantic", "jazz", "pop", "chinese", "electronic", "beginner", "cinematic", "new_age", "game", "custom"}, "custom" if mapped else "classical"),
            base_style=_safe_choice(base_style, {"classical", "romantic", "jazz", "pop", "chinese", "electronic", "beginner", "cinematic", "new_age", "game", "custom"}, base_style),
            custom_style_tags=tags,
            style_profile=mapped,
            difficulty=_safe_choice(intent.difficulty, {"beginner", "intermediate", "advanced"}, "intermediate"),
            meter=intent.time_signature if intent.time_signature in {"4/4", "3/4", "6/8"} else "4/4",
            key=intent.key or "C major",
            length_measures=max(1, int(intent.bars or len(plan.measures) or 16)),
            rhythmic_density=_normalize_density(mapped.get("rhythmic_density") or intent.rhythmic_density),
            syncopation=str(mapped.get("syncopation") or "low"),
            texture=_normalize_texture(str(mapped.get("texture") or intent.texture)),
            accompaniment_style=str(mapped.get("accompaniment_style") or "bass_chord"),
            harmony_flavor=str(mapped.get("harmony_flavor") or "diatonic"),
            cadence_strength=str(mapped.get("cadence_strength") or "clear"),
            dynamic_contrast=str(mapped.get("dynamic_contrast") or "medium"),
            register_bias=str(mapped.get("register_bias") or "middle"),
            timbre_hint=str(mapped.get("timbre_hint") or ""),
            requires_accompaniment=any("piano" in item.lower() for item in intent.instruments) or intent.texture != "single_line",
            run_seed=int(getattr(intent, "run_seed", 0) or 0),
            seed_source=str(getattr(intent, "seed_source", "") or ""),
            variant_id=str(getattr(intent, "variant_id", "") or ""),
            generation_nonce=str(getattr(intent, "generation_nonce", "") or ""),
        )
        style_for_rules = profile.base_style if profile.style == "custom" else profile.style
        if style_for_rules == "romantic" or any(word in prompt for word in ["chopin", "nocturne", "\u8096\u90a6\u611f"]):
            profile.texture = "arpeggiated"
            profile.accompaniment_style = "arpeggiated_chords"
        if "waltz" in prompt or "\u534e\u5c14\u5179" in prompt or profile.meter == "3/4":
            profile.texture = "waltz"
            profile.accompaniment_style = "waltz_bass"
        if style_for_rules == "chinese" or "\u4e2d\u56fd" in prompt or "\u4e94\u58f0" in prompt:
            profile.texture = "pentatonic_open_texture"
            profile.accompaniment_style = "simple_pedal_point"
        if any(word in prompt for word in ["\u9644\u70b9", "dotted"]):
            profile.requires_dotted_rhythm = True
            profile.rhythmic_density = "high" if profile.difficulty != "beginner" else "medium"
        if any(word in prompt for word in ["\u6d3b\u6cfc", "\u6d41\u52a8", "flowing", "lively"]):
            profile.rhythmic_density = "high" if profile.difficulty != "beginner" else "medium"
        if profile.difficulty == "beginner":
            profile.min_pitch_range = 5
            profile.max_consecutive_quarters = 4
            profile.accompaniment_style = "sparse_beginner_bass"
        for constraint in intent.constraints:
            if str(constraint).startswith("accompaniment_style:"):
                profile.accompaniment_style = str(constraint).split(":", 1)[1]
            if str(constraint).startswith("texture:"):
                profile.texture = _normalize_texture(str(constraint).split(":", 1)[1])
            if str(constraint).startswith("rhythmic_density:"):
                profile.rhythmic_density = _normalize_density(str(constraint).split(":", 1)[1])
            if str(constraint).startswith("cadence_strength:"):
                profile.cadence_strength = str(constraint).split(":", 1)[1]
            if str(constraint).startswith("difficulty:"):
                profile.difficulty = _safe_choice(str(constraint).split(":", 1)[1], {"beginner", "intermediate", "advanced"}, profile.difficulty)
            if str(constraint).startswith("variation_seed:"):
                profile.variation_seed = str(constraint).split(":", 1)[1][:120]
            if str(constraint).startswith("run_seed:"):
                profile.run_seed = _safe_int(str(constraint).split(":", 1)[1], profile.run_seed)
                if not profile.variation_seed:
                    profile.variation_seed = str(profile.run_seed)
            if str(constraint).startswith("seed_source:"):
                profile.seed_source = str(constraint).split(":", 1)[1][:80]
            if str(constraint).startswith("variant_id:"):
                profile.variant_id = str(constraint).split(":", 1)[1][:120]
            if str(constraint).startswith("variation_index:"):
                profile.variation_index = _safe_int(str(constraint).split(":", 1)[1], profile.variation_index)
        if profile.run_seed and not profile.variation_seed:
            profile.variation_seed = str(profile.run_seed)
        return profile

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_texture(value: str) -> str:
    clean = str(value or "").replace("-", "_").lower()
    aliases = {
        "single_line": "monophonic",
        "simple_counterpoint": "melody_accompaniment",
        "arpeggiated": "arpeggiated",
        "chordal": "chordal",
        "waltz": "waltz",
        "alberti": "alberti",
        "bass_chord": "bass_chord",
        "ostinato": "ostinato",
        "ostinato_melody": "ostinato_melody",
        "chordal_arpeggiated": "chordal_arpeggiated",
        "pentatonic_open_texture": "pentatonic_open_texture",
    }
    return aliases.get(clean, clean or "melody_accompaniment")


def _normalize_density(value: Any) -> str:
    clean = str(value or "medium").replace("-", "_").lower()
    if clean in {"medium_high", "high_medium"}:
        return "high"
    if clean in {"low_medium", "medium_low"}:
        return "medium"
    return _safe_choice(clean, {"low", "medium", "high"}, "medium")


def _safe_choice(value: Any, allowed: set[str], fallback: str) -> str:
    clean = str(value or fallback).replace("-", "_").lower()
    return clean if clean in allowed else fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback

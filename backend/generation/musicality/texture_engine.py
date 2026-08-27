"""Texture selection for V0.9 generation."""

from __future__ import annotations

from backend.generation.musicality.generation_profile import GenerationProfile


class TextureEngine:
    def generate(self, profile: GenerationProfile, measure_count: int) -> dict[str, object]:
        base = self.choose_texture(profile)
        measures = []
        for number in range(1, measure_count + 1):
            texture = base
            if measure_count >= 8 and number > measure_count // 2 and base == "melody_accompaniment":
                texture = "bass_chord"
            measures.append({"measure": number, "texture": texture})
        return {
            "engine": "texture_engine_v09",
            "texture": base,
            "style_parameters_applied": {"texture": profile.texture},
            "measures": measures,
        }

    @staticmethod
    def choose_texture(profile: GenerationProfile) -> str:
        if profile.texture in {"waltz", "alberti", "bass_chord", "arpeggiated", "chordal", "pentatonic_open_texture", "ostinato", "ostinato_melody", "chordal_arpeggiated"}:
            return profile.texture
        if profile.base_style == "romantic" or profile.style == "romantic":
            return "arpeggiated"
        if profile.difficulty == "beginner":
            return "melody_accompaniment"
        return profile.texture or "melody_accompaniment"

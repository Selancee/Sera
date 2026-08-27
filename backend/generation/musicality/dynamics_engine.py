"""Basic dynamics and phrase expression for V0.9."""

from __future__ import annotations

from backend.generation.musicality.generation_profile import GenerationProfile


class DynamicsEngine:
    def generate(self, profile: GenerationProfile, measure_count: int) -> dict[str, object]:
        base = "mp" if profile.difficulty == "beginner" else "mf"
        if profile.dynamic_contrast == "low":
            base = "mp"
        elif profile.dynamic_contrast == "high" and profile.difficulty != "beginner":
            base = "mf"
        measures = []
        for number in range(1, measure_count + 1):
            dynamic = base
            expression = ""
            if measure_count >= 8 and number > measure_count // 2:
                dynamic = "f" if profile.cadence_strength == "strong" else "mf"
                if profile.dynamic_contrast == "low":
                    dynamic = "mp"
                elif profile.dynamic_contrast == "high" and profile.difficulty != "beginner":
                    dynamic = "f"
            if number % 4 == 3 and profile.difficulty != "beginner":
                expression = "crescendo"
            if number % 4 == 0:
                expression = "diminuendo" if number != measure_count else "cadence emphasis"
            measures.append({"measure": number, "dynamic": dynamic, "expression": expression})
        return {
            "engine": "dynamics_engine_v09",
            "base_dynamic": base,
            "measures": measures,
            "style_parameters_applied": {"dynamic_contrast": profile.dynamic_contrast},
        }

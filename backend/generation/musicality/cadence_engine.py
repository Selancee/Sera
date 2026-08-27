"""Phrase cadence planner for V0.9."""

from __future__ import annotations

from backend.generation.musicality.generation_profile import GenerationProfile


class CadenceEngine:
    def generate(self, profile: GenerationProfile, measure_count: int) -> dict[str, object]:
        measures = []
        for number in range(1, measure_count + 1):
            cadence = "none"
            if number == measure_count:
                if profile.cadence_strength == "loopable":
                    cadence = "loopable"
                else:
                    style = profile.base_style if profile.style == "custom" else profile.style
                    cadence = "modal_pentatonic_ending" if style == "chinese" else "authentic"
            elif number % 4 == 0:
                cadence = "half"
            measures.append({"measure": number, "cadence": cadence, "strength": profile.cadence_strength})
        return {
            "engine": "cadence_engine_v09",
            "measures": measures,
            "final_cadence": measures[-1]["cadence"] if measures else "none",
            "style_parameters_applied": {"cadence_strength": profile.cadence_strength},
        }

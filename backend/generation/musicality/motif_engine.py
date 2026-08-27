"""Motif generation and variation for V0.9."""

from __future__ import annotations

from typing import Any

from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.melodic_style_engine import build_melodic_style_profile, generate_phrase_degree_labels
from backend.generation.musicality.variation import variation_offset
from backend.generation.seed_service import create_run_seed, make_seeded_rng


class MotifEngine:
    def generate(self, profile: GenerationProfile, measure_count: int) -> dict[str, Any]:
        mode = "minor" if "minor" in profile.key.lower() else "major"
        style_profile_payload = dict(profile.style_profile or {})
        style_profile_payload.setdefault("base_style", profile.base_style)
        style_profile_payload.setdefault("custom_style_tags", list(profile.custom_style_tags or []))
        style_profile_payload.setdefault("texture", profile.texture)
        style_profile_payload.setdefault("harmony_flavor", profile.harmony_flavor)
        melodic_profile = build_melodic_style_profile(style_profile_payload, profile.key, mode, profile.difficulty)
        run_seed = profile.run_seed or create_run_seed(profile.key, {"variation_seed": profile.variation_seed or profile.key})
        seed_rng = make_seeded_rng(run_seed, "motif:seed")
        seed = [str(item) for item in melodic_profile.get("seed_degree_labels", [])] or [
            str(item) for item in generate_phrase_degree_labels(melodic_profile, "opening", int(melodic_profile.get("motif_length", 4)), seed_rng)
        ]
        if seed:
            shift = variation_offset(profile.variation_seed or str(run_seed), len(seed), "motif:seed:rotate")
            seed = seed[shift:] + seed[:shift]
        measures = []
        for number in range(1, measure_count + 1):
            section = "B" if measure_count >= 8 and measure_count // 2 < number <= measure_count * 3 // 4 else "A"
            cadence = number % 4 == 0 or number == measure_count
            strategy = self._strategy_for_measure(profile, number, section, cadence)
            phrase_role = "final" if number == measure_count else "cadence" if cadence else "contrast" if section == "B" else "opening"
            rng = make_seeded_rng(run_seed, f"motif:{number}:{strategy}")
            degrees = generate_phrase_degree_labels(melodic_profile, phrase_role, 8, rng)
            measures.append({"measure": number, "section": section, "strategy": strategy, "degrees": degrees, "phrase_role": phrase_role})
        return {
            "engine": "motif_engine_v094",
            "seed_motif": seed,
            "variation_seed": profile.variation_seed,
            "run_seed": run_seed,
            "motif_source": "melodic_style_engine",
            "melodic_style_profile": melodic_profile,
            "pitch_vocabulary": melodic_profile.get("pitch_vocabulary", "diatonic"),
            "contour_policy": melodic_profile.get("contour_policy", "balanced"),
            "interval_policy": melodic_profile.get("interval_policy", "mostly_stepwise"),
            "measures": measures,
        }

    @staticmethod
    def _seed_motif(profile: GenerationProfile) -> list[str]:
        if "minor" in profile.key.lower():
            variants = [["1", "2", "b3", "5"], ["1", "5", "b3", "4"], ["5", "b3", "2", "1"]]
        else:
            variants = [["1", "2", "3", "5"], ["1", "3", "5", "6"], ["5", "3", "2", "1"], ["1", "4", "3", "6"]]
        return variants[variation_offset(profile.variation_seed, len(variants), "motif:seed")]

    @staticmethod
    def _strategy_for_measure(profile: GenerationProfile, number: int, section: str, cadence: bool) -> str:
        if not profile.variation_seed:
            return "cadence_resolution" if cadence else "sequence_up" if section == "B" and number % 2 else "repeat" if number <= 4 else "rhythmic_variation"
        if cadence:
            return "cadence_resolution"
        shift = variation_offset(profile.variation_seed, 3, "motif:strategy") + profile.variation_index
        if section == "B":
            return ["sequence_up", "sequence_down", "inversion"][(number + shift) % 3]
        if number <= 4:
            return ["repeat", "rhythmic_variation", "interval_expansion"][(number + shift) % 3]
        return ["rhythmic_variation", "interval_expansion", "interval_contraction"][(number + shift) % 3]

    @staticmethod
    def degrees_for_measure(seed: list[str], strategy: str, measure_number: int, count: int = 8) -> list[str]:
        if strategy == "sequence_up":
            motif = shift_degrees(seed, 1)
        elif strategy == "sequence_down":
            motif = shift_degrees(seed, -1)
        elif strategy == "inversion":
            motif = list(reversed(seed))
        elif strategy == "interval_expansion":
            motif = [seed[0], "5", seed[2], "6"]
        elif strategy == "interval_contraction":
            motif = [seed[0], "2", seed[1], "3"]
        elif strategy == "cadence_resolution":
            motif = ["5", "4", "2", "1"]
        elif measure_number % 3 == 0:
            motif = [seed[0], seed[2], seed[1], seed[3]]
        else:
            motif = list(seed)
        while len(motif) < count:
            motif.extend(motif)
        return motif[:count]


def shift_degrees(degrees: list[str], delta: int) -> list[str]:
    scale = ["1", "2", "3", "4", "5", "6", "7"]
    out = []
    for degree in degrees:
        clean = "3" if degree == "b3" else "6" if degree == "b6" else degree
        if clean in scale:
            out.append(scale[(scale.index(clean) + delta) % len(scale)])
        else:
            out.append(degree)
    return out

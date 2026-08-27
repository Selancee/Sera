"""Candidate-set generation before selecting a final V0.96 score."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Callable

from backend.generation.candidate_ranker import CandidateRanker
from backend.generation.seed_service import create_variant_id
from backend.models.schemas import CompositionPlan, ValidationResult


GeneratedCallback = Callable[[CompositionPlan], Any]
ValidationCallback = Callable[[CompositionPlan, Any], ValidationResult]


def clamp_candidate_count(value: Any, default: int = 4) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = default
    return max(3, min(8, count))


def generate_candidate_set(
    plan: CompositionPlan,
    generate_one: GeneratedCallback,
    validate_one: ValidationCallback,
    candidate_count: int = 4,
) -> dict[str, Any]:
    """Generate K deterministic candidates and return a ranked bundle."""

    count = clamp_candidate_count(candidate_count)
    parent_run_seed = int(getattr(plan.intent, "run_seed", 0) or _seed_from_text(plan.intent.prompt or plan.intent.raw_prompt or "sera"))
    candidates: list[dict[str, Any]] = []
    for candidate_index in range(count):
        candidate_seed = _candidate_seed(parent_run_seed, candidate_index)
        candidate_plan = _candidate_plan(plan, parent_run_seed, candidate_seed, candidate_index, count)
        generated = generate_one(candidate_plan)
        validation = validate_one(candidate_plan, generated)
        generated.metadata = dict(generated.metadata or {})
        generated.metadata["candidate_index"] = candidate_index
        generated.metadata["candidate_count"] = count
        generated.metadata["candidate_seed"] = candidate_seed
        generated.metadata["parent_run_seed"] = parent_run_seed
        profile = dict(generated.metadata.get("generation_profile") or {})
        profile.setdefault("parent_run_seed", parent_run_seed)
        profile["candidate_index"] = candidate_index
        profile["candidate_count"] = count
        profile["candidate_seed"] = candidate_seed
        generated.metadata["generation_profile"] = profile
        candidates.append(
            {
                "candidate_index": candidate_index,
                "candidate_seed": candidate_seed,
                "parent_run_seed": parent_run_seed,
                "candidate_count": count,
                "plan": candidate_plan,
                "generated": generated,
                "validation": validation,
            }
        )
    return CandidateRanker().rank(candidates)


def _candidate_plan(plan: CompositionPlan, parent_seed: int, candidate_seed: int, candidate_index: int, candidate_count: int) -> CompositionPlan:
    candidate = copy.deepcopy(plan)
    intent = candidate.intent
    intent.run_seed = candidate_seed
    intent.variant_id = create_variant_id(parent_seed, candidate_index)
    intent.constraints = [
        str(item)
        for item in intent.constraints
        if not str(item).startswith(("run_seed:", "variation_seed:", "variation_index:", "variant_id:", "candidate_index:", "candidate_count:", "parent_run_seed:"))
    ]
    intent.constraints.extend(
        [
            f"run_seed:{candidate_seed}",
            f"variation_seed:{parent_seed}:candidate:{candidate_index}",
            f"variation_index:{candidate_index}",
            f"variant_id:{intent.variant_id}",
            f"candidate_index:{candidate_index}",
            f"candidate_count:{candidate_count}",
            f"parent_run_seed:{parent_seed}",
        ]
    )
    variation_profile = _candidate_variation_profile(candidate_index)
    intent.resolved_generation_request = dict(intent.resolved_generation_request or {})
    intent.resolved_generation_request.update(
        {
            "run_seed": parent_seed,
            "candidate_seed": candidate_seed,
            "candidate_index": candidate_index,
            "candidate_count": candidate_count,
            "variant_id": intent.variant_id,
            "candidate_variation_profile": variation_profile,
        }
    )
    for measure in candidate.measures:
        if candidate_index % 3 == 1 and measure.rhythmic_density != "low":
            measure.motif_strategy = "rhythmic_variation"
        elif candidate_index % 3 == 2 and measure.cadence == "none":
            measure.motif_strategy = "sequence_up" if measure.index % 2 else "sequence_down"
    return candidate


def _candidate_variation_profile(candidate_index: int) -> dict[str, str]:
    melody = ["expectation_arch", "expectation_hook", "expectation_gap_fill", "expectation_cadential"][candidate_index % 4]
    rhythm = ["base_density", "displaced_eighths", "dotted_variant", "rest_variant"][candidate_index % 4]
    harmony = ["profile_cell_a", "profile_cell_b", "cadence_weighted", "color_tone_weighted"][candidate_index % 4]
    voicing = ["close", "open", "rootless_or_pedal", "register_shift"][candidate_index % 4]
    accompaniment = ["bass_chord", "arpeggiated", "pedal_or_ostinato", "syncopated"][candidate_index % 4]
    register = ["middle", "middle_high", "middle_low", "wider"][candidate_index % 4]
    cadence = ["clear", "strong", "half_then_authentic", "delayed_resolution"][candidate_index % 4]
    return {
        "melody_variant": melody,
        "rhythm_variant": rhythm,
        "harmony_variant": harmony,
        "voicing_variant": voicing,
        "accompaniment_variant": accompaniment,
        "register_variant": register,
        "cadence_variant": cadence,
    }


def _candidate_seed(parent_seed: int, candidate_index: int) -> int:
    return _seed_from_text(f"{int(parent_seed)}:candidate:{int(candidate_index)}")


def _seed_from_text(text: str) -> int:
    digest = hashlib.sha256(str(text).encode("utf-8")).hexdigest()
    return int(digest[:16], 16) & ((1 << 63) - 1)

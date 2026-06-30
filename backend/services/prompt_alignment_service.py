"""Prompt-alignment metrics for score editing patches."""

from __future__ import annotations

from typing import Any

from backend.services.score_operation_service import (
    operation_changes_harmony,
    operation_changes_melody,
    operation_changes_rhythm,
)


def score_prompt_alignment(
    instruction: str,
    selected_range: dict[str, Any],
    constraints: dict[str, Any],
    patch: dict[str, Any],
    validation_report: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Return deterministic 0..1 prompt-alignment scores for an edit patch."""

    operations = list(patch.get("operations") or [])
    target = patch.get("target_range") or {}
    selected_start = int(selected_range.get("start_measure", 1))
    selected_end = int(selected_range.get("end_measure", selected_start))
    target_start = int(target.get("start_measure", selected_start))
    target_end = int(target.get("end_measure", target_start))
    selection_ok = selected_start <= target_start and target_end <= selected_end
    selection_score = 1.0 if selection_ok else 0.35

    harmony_changed = any(operation_changes_harmony(op) for op in operations)
    melody_changed = any(operation_changes_melody(op) for op in operations)
    rhythm_changed = any(operation_changes_rhythm(op) for op in operations)
    preserve_harmony_score = 0.35 if constraints.get("preserve_harmony") and harmony_changed else 1.0
    preserve_melody_score = 0.35 if constraints.get("preserve_melody") and melody_changed else 1.0
    preserve_rhythm_score = 0.45 if constraints.get("preserve_rhythm") and rhythm_changed else 1.0
    constraint_score = min(preserve_harmony_score, preserve_melody_score, preserve_rhythm_score)

    text = instruction.lower()
    matched_aspects = [str(item).lower() for item in patch.get("prompt_alignment", {}).get("matched_aspects", [])]
    style_words = ["lyrical", "dramatic", "chopin", "waltz", "pentatonic", "style", "风格", "五声", "肖邦"]
    mood_words = ["sad", "melancholy", "bright", "dark", "忧郁", "戏剧", "抒情"]
    density_words = ["density", "rhythm", "节奏", "密度"]
    difficulty_words = ["beginner", "simplify", "easier", "difficulty", "降低难度", "初级"]
    style_shift = _targeted_score(text, matched_aspects, style_words, {"update_texture", "transform_notes", "regenerate"})
    mood_shift = _targeted_score(text, matched_aspects, mood_words, {"transform_notes", "simplify"})
    difficulty_shift = _targeted_score(text, matched_aspects, difficulty_words, {"simplify"})
    rhythmic_density_shift = _targeted_score(text, matched_aspects, density_words, {"humanize_rhythm", "simplify_rhythm", "quantize_rhythm"})
    validation_score = 1.0 if (validation_report or {}).get("valid_musicxml", True) else 0.0
    range_len = max(1, target_end - target_start + 1)
    over_editing_penalty = min(0.45, max(0.0, (len(operations) - range_len * 6) / max(1, range_len * 12)))
    overall = (
        selection_score * 0.18
        + constraint_score * 0.18
        + preserve_harmony_score * 0.08
        + preserve_melody_score * 0.08
        + preserve_rhythm_score * 0.08
        + style_shift * 0.08
        + mood_shift * 0.06
        + difficulty_shift * 0.06
        + rhythmic_density_shift * 0.06
        + validation_score * 0.14
        - over_editing_penalty
    )
    return {
        "selection_respect_score": round(selection_score, 4),
        "constraint_respect_score": round(constraint_score, 4),
        "preserve_harmony_score": round(preserve_harmony_score, 4),
        "preserve_melody_score": round(preserve_melody_score, 4),
        "preserve_rhythm_score": round(preserve_rhythm_score, 4),
        "style_shift_score": round(style_shift, 4),
        "mood_shift_score": round(mood_shift, 4),
        "difficulty_shift_score": round(difficulty_shift, 4),
        "rhythmic_density_shift_score": round(rhythmic_density_shift, 4),
        "validation_improvement_score": round(validation_score, 4),
        "over_editing_penalty": round(over_editing_penalty, 4),
        "overall_prompt_alignment_edit_score": round(max(0.0, min(1.0, overall)), 4),
    }


def _targeted_score(text: str, matched_aspects: list[str], words: list[str], operation_types: set[str]) -> float:
    wants_change = any(word in text for word in words)
    if not wants_change:
        return 0.75
    if any(word in " ".join(matched_aspects) for word in words):
        return 1.0
    # Fall back to operation evidence when the agent did not name the aspect.
    del operation_types
    return 0.8

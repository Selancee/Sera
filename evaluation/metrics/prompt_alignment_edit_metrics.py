"""Evaluation wrapper for V0.6 prompt-aligned score editing."""

from __future__ import annotations

from typing import Any

from backend.services.prompt_alignment_service import score_prompt_alignment


def prompt_alignment_edit_metrics(
    instruction: str,
    selected_range: dict[str, Any],
    constraints: dict[str, Any],
    patch: dict[str, Any],
    validation_report: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Return score-editing prompt alignment metrics."""

    return score_prompt_alignment(instruction, selected_range, constraints, patch, validation_report)


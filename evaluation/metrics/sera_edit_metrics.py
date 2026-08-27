"""Deterministic task-level metrics for SeraEdit conditions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.validation.musicxml_validator import MusicXMLValidator
from evaluation.conditions.sera_edit_conditions import ConditionOutcome
from scripts.validate_benchmark import evaluate_constraints
from sera_edit.domain.score_scope import ScoreScope
from sera_edit.execution.diff_engine import score_diff
from sera_edit.validation.protected_scope_validator import validate_protected_scope


def _changed_ids(diff: dict[str, Any]) -> set[str]:
    result = {
        f"deleted:{item['event_id']}" for item in diff.get("deleted", [])
    } | {
        f"changed:{item['event_id']}" for item in diff.get("changed", [])
    }
    # Inserted IDs are generator-owned. Compare their musical/structural
    # placement so equivalent patches are not penalized for using a different
    # valid stable ID than the Gold patch.
    for item in diff.get("added", []):
        event = item.get("after") or {}
        result.add(
            "added:"
            + ":".join(
                str(value)
                for value in (
                    item.get("measure"),
                    item.get("staff"),
                    item.get("voice"),
                    item.get("offset"),
                    event.get("type"),
                    event.get("pitch"),
                    event.get("duration"),
                )
            )
        )
    result.update(f"global:{name}" for name in diff.get("global_changes", {}))
    return result


def compute_task_metrics(
    task: dict[str, Any],
    source_score: dict[str, Any],
    outcome: ConditionOutcome,
    expected_score: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute metrics without asking the generating provider to judge itself."""

    expected_refusal = task["expected_status"] == "refuse"
    correct_refusal = expected_refusal and outcome.refusal
    unsafe_execution = expected_refusal and not outcome.refusal and outcome.score_document is not None
    if expected_refusal:
        task_success = correct_refusal
        constraints_satisfied = 1 if correct_refusal else 0
        constraint_total = 1
    elif outcome.score_document is None or outcome.refusal:
        task_success = False
        constraints_satisfied = 0
        constraint_total = len(task["expected_constraints"])
    else:
        per_constraint = [
            evaluate_constraints(source_score, outcome.score_document, [constraint])[0]
            for constraint in task["expected_constraints"]
        ]
        constraints_satisfied = sum(1 for value in per_constraint if value)
        constraint_total = len(per_constraint)
        task_success = all(per_constraint)
    musicxml_valid = False
    if outcome.musicxml:
        musicxml_valid = MusicXMLValidator().validate_text(outcome.musicxml).valid
    preservation_rate = 1.0 if correct_refusal else 0.0
    preservation_complete = correct_refusal
    actual_diff: dict[str, Any] = {}
    if outcome.score_document is not None:
        actual_diff = score_diff(source_score, outcome.score_document)
        preservation = validate_protected_scope(
            source_score,
            outcome.score_document,
            ScoreScope.from_dict(task["target_scope"]),
            ScoreScope.from_dict(task["protected_scope"]),
        )
        preservation_rate = float(preservation.checks["preservation_rate"])
        preservation_complete = not preservation.errors
    minimality = 1.0 if correct_refusal else 0.0
    element_change_precision = 1.0 if correct_refusal else 0.0
    if expected_score is not None and outcome.score_document is not None:
        gold_ids = _changed_ids(score_diff(source_score, expected_score))
        actual_ids = _changed_ids(actual_diff)
        minimality = min(1.0, len(gold_ids) / max(1, len(actual_ids)))
        element_change_precision = len(gold_ids & actual_ids) / max(1, len(actual_ids))
    provider_responses = outcome.all_provider_responses
    provider_latency = sum(float(response.latency_ms or 0) for response in provider_responses)
    input_tokens = sum(int(response.input_tokens or 0) for response in provider_responses)
    output_tokens = sum(int(response.output_tokens or 0) for response in provider_responses)
    estimated_cost = sum(float(response.estimated_cost or 0.0) for response in provider_responses)
    repair_cost = sum(float(response.estimated_cost or 0.0) for response in outcome.repair_responses)
    return {
        "task_id": task["task_id"],
        "category": task["category"],
        "condition": outcome.condition,
        "expected_status": task["expected_status"],
        "refused": int(outcome.refusal),
        "output_produced": int(outcome.score_document is not None or bool(outcome.musicxml)),
        "musicxml_validity": "" if correct_refusal else int(musicxml_valid),
        "patch_parse": "" if outcome.patch_parsed is None else int(outcome.patch_parsed),
        "task_success": int(task_success),
        "non_target_preservation": preservation_rate,
        "complete_preservation": int(preservation_complete),
        "operation_minimality": minimality,
        "element_change_precision": element_change_precision,
        "constraints_satisfied": constraints_satisfied,
        "constraint_total": constraint_total,
        "constraint_satisfaction": constraints_satisfied / max(1, constraint_total),
        "correct_refusal": int(correct_refusal),
        "unsafe_execution": int(unsafe_execution),
        "repair_attempted": int(outcome.repair_attempted),
        "repair_success": int(outcome.repair_success),
        "repair_attempt_count": outcome.repair_attempt_count,
        "repair_added_cost": repair_cost,
        "provider_latency_ms": provider_latency,
        "processing_latency_ms": outcome.processing_latency_ms,
        "latency_ms": provider_latency + outcome.processing_latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost": estimated_cost,
        "error_codes": ";".join(outcome.error_codes),
        "error": outcome.error or "",
    }

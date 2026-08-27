"""Pre-apply structural, selector, and scope validation."""

from __future__ import annotations

from typing import Any

from sera_edit.domain.score_patch import ScorePatch
from sera_edit.domain.score_scope import ScoreScope, iter_event_contexts
from sera_edit.validation.validation_report import ValidationIssue, ValidationReport


GLOBAL_OPERATIONS = {"change_key_signature", "change_time_signature"}
INSERT_OPERATIONS = {"insert_note", "insert_rest"}
EVENT_REQUIRED = {
    "set_pitch",
    "set_duration",
    "delete_event",
    "set_dynamic",
    "set_articulation",
    "set_tie",
    "set_slur",
    "move_to_voice",
}


def _selector(operation: Any) -> ScoreScope:
    payload = dict(operation.selector)
    if "event_id" in payload and "event_ids" not in payload:
        payload["event_ids"] = [payload.pop("event_id")]
    if "measure" in payload and "measures" not in payload:
        payload["measures"] = [payload.pop("measure")]
    return ScoreScope.from_dict(payload)


def validate_structure(score: dict[str, Any], patch: ScorePatch) -> ValidationReport:
    """Check IDs, selectors, target containment, and protected overlap."""

    report = ValidationReport()
    contexts = list(iter_event_contexts(score))
    existing_ids = {context.event_id for context in contexts}
    measure_numbers = {int(item.get("number", 0)) for item in score.get("measures") or []}
    operation_ids: set[str] = set()
    for operation in patch.operations:
        if operation.operation_id in operation_ids:
            report.add_error(ValidationIssue("E04", f"duplicate operation_id: {operation.operation_id}", "structural"))
        operation_ids.add(operation.operation_id)
        selector = _selector(operation)
        if operation.type in INSERT_OPERATIONS | GLOBAL_OPERATIONS:
            selected = []
        else:
            selected = selector.select(score) if not selector.empty else patch.target_scope.select(score)
        if operation.type in EVENT_REQUIRED | {"transpose", "duplicate_motif", "replace_chord"} and not selected:
            report.add_error(
                ValidationIssue("E06", f"operation {operation.operation_id} selected no existing events", "structural")
            )
        for context in selected:
            if not patch.target_scope.contains(context):
                report.add_error(
                    ValidationIssue(
                        "E05",
                        f"operation {operation.operation_id} targets {context.event_id} outside target_scope",
                        "structural",
                        details=context.location(),
                    )
                )
            if patch.protected_scope.contains(context):
                report.add_error(
                    ValidationIssue(
                        "E11",
                        f"operation {operation.operation_id} targets protected event {context.event_id}",
                        "protected_scope",
                        details=context.location(),
                    )
                )
        if operation.type in INSERT_OPERATIONS:
            raw_measure = operation.selector.get("measure") or (operation.selector.get("measures") or [None])[0]
            if raw_measure is None or int(raw_measure) not in measure_numbers:
                report.add_error(ValidationIssue("E05", f"operation {operation.operation_id} has invalid target measure", "structural"))
            elif patch.target_scope.measures and int(raw_measure) not in patch.target_scope.measures:
                report.add_error(ValidationIssue("E05", f"insert target measure {raw_measure} is outside target_scope", "structural"))
        if operation.type == "duplicate_motif":
            target_measure = int(operation.arguments.get("target_measure", 0))
            if target_measure not in measure_numbers:
                report.add_error(ValidationIssue("E05", f"duplicate target measure {target_measure} does not exist", "structural"))
            elif patch.target_scope.measures and target_measure not in patch.target_scope.measures:
                report.add_error(ValidationIssue("E05", f"duplicate target measure {target_measure} is outside target_scope", "structural"))
        if operation.type in GLOBAL_OPERATIONS and not patch.target_scope.whole_score:
            report.add_error(ValidationIssue("E05", f"{operation.type} requires target_scope.whole_score=true", "structural"))
        requested = set(operation.selector.get("event_ids") or [])
        if operation.selector.get("event_id"):
            requested.add(str(operation.selector["event_id"]))
        for missing in sorted(requested - existing_ids):
            report.add_error(ValidationIssue("E06", f"event does not exist: {missing}", "structural"))
    report.checks.update(
        {
            "event_count": len(contexts),
            "measure_count": len(measure_numbers),
            "operation_ids_unique": len(operation_ids) == len(patch.operations),
        }
    )
    return report

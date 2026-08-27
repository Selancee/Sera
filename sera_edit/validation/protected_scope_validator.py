"""Protected and non-target preservation validation."""

from __future__ import annotations

from typing import Any

from sera_edit.domain.score_scope import ScoreScope, iter_event_contexts
from sera_edit.execution.diff_engine import score_diff
from sera_edit.validation.validation_report import ValidationIssue, ValidationReport


def validate_protected_scope(
    before: dict[str, Any],
    after: dict[str, Any],
    target_scope: ScoreScope,
    protected_scope: ScoreScope,
) -> ValidationReport:
    """Reject explicit protected edits and all changes outside target scope."""

    report = ValidationReport()
    diff = score_diff(before, after)
    before_contexts = {context.event_id: context for context in iter_event_contexts(before)}
    after_contexts = {context.event_id: context for context in iter_event_contexts(after)}
    protected_ids = {
        event_id
        for event_id, context in before_contexts.items()
        if protected_scope.contains(context) or not target_scope.contains(context)
    }
    violation_details: list[dict[str, Any]] = []
    for item in diff["deleted"]:
        if item["event_id"] in protected_ids:
            violation_details.append({"kind": "deleted", "event_id": item["event_id"]})
    for item in diff["changed"]:
        event_id = item["event_id"]
        before_context = before_contexts[event_id]
        after_context = after_contexts[event_id]
        if event_id in protected_ids or protected_scope.contains(after_context) or not target_scope.contains(after_context):
            violation_details.append(
                {"kind": "changed", "event_id": event_id, "changed_fields": item["changed_fields"]}
            )
    for item in diff["added"]:
        context = after_contexts[item["event_id"]]
        if protected_scope.contains(context) or not target_scope.contains(context):
            violation_details.append({"kind": "added", "event_id": item["event_id"]})
    if diff["global_changes"] and not target_scope.whole_score:
        violation_details.append({"kind": "global", "fields": sorted(diff["global_changes"])})
    for details in violation_details:
        report.add_error(
            ValidationIssue("E11", f"protected scope violation: {details['kind']}", "protected_scope", details=details)
        )
    protected_count = len(protected_ids)
    violations = len(violation_details)
    report.checks.update(
        {
            "unexpected_changed_elements": violations,
            "protected_element_count": protected_count,
            "preservation_rate": 1.0 - violations / max(1, protected_count),
            "violation_details": violation_details,
        }
    )
    return report

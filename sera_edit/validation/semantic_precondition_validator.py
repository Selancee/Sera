"""Deterministic semantic pre- and postcondition validation."""

from __future__ import annotations

from typing import Any

from sera_edit.execution.diff_engine import score_diff
from sera_edit.validation.validation_report import ValidationIssue, ValidationReport


SUPPORTED_PRECONDITIONS = {"event_exists", "preserve_duration", "preserve_pitch", "minimum_event_count"}


def validate_preconditions(score: dict[str, Any], preconditions: tuple[dict[str, Any], ...]) -> ValidationReport:
    """Validate known preconditions and reject unknown semantics explicitly."""

    report = ValidationReport()
    event_ids = {
        str(event.get("event_id", ""))
        for measure in score.get("measures") or []
        for event in measure.get("events") or []
    }
    for condition in preconditions:
        kind = str(condition.get("type", ""))
        if kind not in SUPPORTED_PRECONDITIONS:
            report.unsupported = True
            report.add_error(ValidationIssue("E19", f"unsupported precondition: {kind}", "semantic"))
        elif kind == "event_exists" and str(condition.get("event_id", "")) not in event_ids:
            report.add_error(ValidationIssue("E06", f"required event does not exist: {condition.get('event_id')}", "semantic"))
        elif kind == "minimum_event_count" and len(event_ids) < int(condition.get("value", 0)):
            report.add_error(ValidationIssue("E15", "minimum event count precondition failed", "semantic"))
    report.checks["precondition_count"] = len(preconditions)
    return report


def validate_postconditions(
    before: dict[str, Any],
    after: dict[str, Any],
    expected_effects: tuple[dict[str, Any], ...],
) -> ValidationReport:
    """Validate deterministic preservation and change-count effects."""

    report = ValidationReport()
    diff = score_diff(before, after)
    for effect in expected_effects:
        kind = str(effect.get("type", ""))
        if kind == "changed_element_count":
            expected = int(effect.get("value", 0))
            if diff["changed_element_count"] != expected:
                report.add_error(ValidationIssue("E15", f"changed {diff['changed_element_count']} elements; expected {expected}", "semantic"))
        elif kind == "preserve_duration":
            offenders = [item["event_id"] for item in diff["changed"] if "duration" in item["changed_fields"]]
            if offenders:
                report.add_error(ValidationIssue("E13", "duration changed despite preserve_duration", "semantic", details={"event_ids": offenders}))
        elif kind == "preserve_pitch":
            offenders = [item["event_id"] for item in diff["changed"] if "pitch" in item["changed_fields"]]
            if offenders:
                report.add_error(ValidationIssue("E12", "pitch changed despite preserve_pitch", "semantic", details={"event_ids": offenders}))
        elif kind not in {"pitch_delta", "dynamic_equals", "meter_equals", "key_equals", "event_inserted", "event_deleted"}:
            report.unsupported = True
            report.add_error(ValidationIssue("E19", f"unsupported expected effect: {kind}", "semantic"))
    report.checks["expected_effect_count"] = len(expected_effects)
    return report

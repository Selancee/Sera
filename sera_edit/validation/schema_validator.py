"""Strict dependency-light validation for ScorePatch 1.0.0."""

from __future__ import annotations

import re
from typing import Any

from sera_edit.domain.score_patch import SCHEMA_VERSION, SUPPORTED_OPERATION_TYPES
from sera_edit.domain.score_scope import ScoreScope
from sera_edit.validation.validation_report import ValidationIssue, ValidationReport


PATCH_FIELDS = {
    "schema_version",
    "patch_id",
    "source_score_id",
    "source_fingerprint",
    "instruction",
    "target_scope",
    "protected_scope",
    "preconditions",
    "operations",
    "expected_effects",
    "provenance",
}
OPERATION_FIELDS = {
    "operation_id",
    "type",
    "selector",
    "arguments",
    "preconditions",
    "expected_change_count",
}
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


def validate_patch_schema(payload: Any) -> ValidationReport:
    """Validate strict shape, operation types, and basic argument contracts."""

    report = ValidationReport()
    if not isinstance(payload, dict):
        report.add_error(ValidationIssue("E03", "patch must be a JSON object", "schema", True))
        return report
    missing = sorted(PATCH_FIELDS - set(payload))
    unknown = sorted(set(payload) - PATCH_FIELDS)
    for field in missing:
        report.add_error(ValidationIssue("E04", f"missing required patch field: {field}", "schema", field == "schema_version"))
    for field in unknown:
        report.add_error(ValidationIssue("E04", f"unknown patch field: {field}", "schema"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        report.add_error(ValidationIssue("E04", f"schema_version must be {SCHEMA_VERSION}", "schema", True))
    for field in ("patch_id", "source_score_id", "instruction"):
        if not isinstance(payload.get(field), str) or not payload.get(field, "").strip():
            report.add_error(ValidationIssue("E04", f"{field} must be a non-empty string", "schema"))
    fingerprint = payload.get("source_fingerprint")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint):
        report.add_error(ValidationIssue("E04", "source_fingerprint must be sha256:<64 lowercase hex characters>", "schema"))
    for field in ("target_scope", "protected_scope", "provenance"):
        if not isinstance(payload.get(field), dict):
            report.add_error(ValidationIssue("E04", f"{field} must be an object", "schema"))
    for field in ("preconditions", "operations", "expected_effects"):
        if not isinstance(payload.get(field), list):
            report.add_error(ValidationIssue("E04", f"{field} must be an array", "schema"))
    try:
        target_scope = ScoreScope.from_dict(payload.get("target_scope"))
        ScoreScope.from_dict(payload.get("protected_scope"))
        if target_scope.empty:
            report.add_error(ValidationIssue("E04", "target_scope must select content or set whole_score=true", "schema"))
    except (TypeError, ValueError) as exc:
        report.add_error(ValidationIssue("E04", f"invalid score scope: {exc}", "schema", True))
    operations = payload.get("operations") if isinstance(payload.get("operations"), list) else []
    for index, operation in enumerate(operations):
        _validate_operation(operation, index, report)
    report.checks["schema_version"] = payload.get("schema_version")
    report.checks["operation_count"] = len(operations)
    return report


def _validate_operation(operation: Any, index: int, report: ValidationReport) -> None:
    if not isinstance(operation, dict):
        report.add_error(ValidationIssue("E04", f"operation {index} must be an object", "schema"))
        return
    for field in sorted({"operation_id", "type", "selector", "arguments", "preconditions"} - set(operation)):
        report.add_error(ValidationIssue("E04", f"operation {index} missing field: {field}", "schema"))
    for field in sorted(set(operation) - OPERATION_FIELDS):
        report.add_error(ValidationIssue("E04", f"operation {index} has unknown field: {field}", "schema"))
    op_id = operation.get("operation_id")
    op_type = operation.get("type")
    selector = operation.get("selector")
    arguments = operation.get("arguments")
    if not isinstance(op_id, str) or not op_id.strip():
        report.add_error(ValidationIssue("E04", f"operation {index} operation_id must be non-empty", "schema"))
    if op_type not in SUPPORTED_OPERATION_TYPES:
        report.unsupported = True
        report.add_error(ValidationIssue("E19", f"unsupported operation type: {op_type}", "schema"))
        return
    if not isinstance(selector, dict) or not isinstance(arguments, dict):
        report.add_error(ValidationIssue("E04", f"operation {index} selector and arguments must be objects", "schema"))
        return
    if not isinstance(operation.get("preconditions"), list):
        report.add_error(ValidationIssue("E04", f"operation {index} preconditions must be an array", "schema"))
    expected_count = operation.get("expected_change_count")
    if expected_count is not None and (not isinstance(expected_count, int) or expected_count < 0):
        report.add_error(ValidationIssue("E04", f"operation {index} expected_change_count must be a non-negative integer", "schema"))
    required_argument = {
        "transpose": "semitones",
        "set_pitch": "pitch",
        "set_duration": "duration",
        "insert_note": "pitch",
        "set_dynamic": "dynamic",
        "set_articulation": "articulations",
        "set_tie": "tie",
        "set_slur": "slur",
        "change_key_signature": "key",
        "change_time_signature": "meter",
        "move_to_voice": "voice",
        "duplicate_motif": "target_measure",
        "replace_chord": "pitches",
        "batch": "operations",
    }.get(str(op_type))
    if required_argument and required_argument not in arguments:
        report.add_error(ValidationIssue("E04", f"operation {index} {op_type} requires arguments.{required_argument}", "schema"))
    if op_type in EVENT_REQUIRED and not (selector.get("event_ids") or selector.get("event_id")):
        report.add_error(ValidationIssue("E05", f"operation {index} {op_type} requires event_ids", "schema"))
    if op_type == "transpose" and not isinstance(arguments.get("semitones"), int):
        report.add_error(ValidationIssue("E04", f"operation {index} transpose semitones must be an integer", "schema", True))
    if op_type == "move_to_voice" and (not isinstance(arguments.get("voice"), int) or arguments.get("voice", 0) < 1):
        report.add_error(ValidationIssue("E04", f"operation {index} voice must be a positive integer", "schema"))
    if op_type in {"insert_note", "insert_rest"}:
        if not (selector.get("measures") or selector.get("measure")):
            report.add_error(ValidationIssue("E05", f"operation {index} {op_type} requires a target measure", "schema"))
    if op_type == "replace_chord" and not isinstance(arguments.get("pitches"), list):
        report.add_error(ValidationIssue("E04", f"operation {index} replace_chord pitches must be an array", "schema"))
    if op_type == "batch" and not isinstance(arguments.get("operations"), list):
        report.add_error(ValidationIssue("E04", f"operation {index} batch operations must be an array", "schema"))

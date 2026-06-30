"""V0.7 validation for previewable ScorePatch payloads."""

from __future__ import annotations

import re
from typing import Any

from backend.services.prompt_alignment_service import score_prompt_alignment
from backend.services.score_document_service import score_document_to_musicxml
from backend.services.score_operation_service import (
    apply_operations,
    operation_changes_harmony,
    operation_changes_melody,
    operation_changes_rhythm,
)
from backend.validation.musicxml_validator import MusicXMLValidator


ALLOWED_PATCH_TYPES = {
    "replace_measures",
    "transform_notes",
    "update_harmony",
    "update_texture",
    "add_cadence",
    "simplify",
    "regenerate",
    "no_op",
}
GLOBAL_OPERATION_TYPES = {"change_key", "change_meter", "change_tempo"}


def validate_score_patch_schema(patch: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate the required ScorePatch shape without an extra dependency."""

    errors: list[str] = []
    if not isinstance(patch, dict):
        return False, ["patch must be an object"]
    for key in [
        "patch_id",
        "patch_type",
        "target_range",
        "operations",
        "rationale",
        "expected_effect",
        "prompt_alignment",
        "validation_expectations",
    ]:
        if key not in patch:
            errors.append(f"missing required field: {key}")
    if patch.get("patch_type") not in ALLOWED_PATCH_TYPES:
        errors.append(f"patch_type must be one of {sorted(ALLOWED_PATCH_TYPES)}")
    target = patch.get("target_range")
    if not isinstance(target, dict):
        errors.append("target_range must be an object")
    else:
        start = _safe_int(target.get("start_measure"), 0)
        end = _safe_int(target.get("end_measure"), 0)
        if start < 1 or end < 1:
            errors.append("target_range measures must be positive")
        if start and end and start > end:
            errors.append("target_range start_measure must be <= end_measure")
    if not isinstance(patch.get("operations"), list):
        errors.append("operations must be an array")
    alignment = patch.get("prompt_alignment")
    if not isinstance(alignment, dict):
        errors.append("prompt_alignment must be an object")
    elif not isinstance(alignment.get("matched_aspects", []), list) or not isinstance(alignment.get("risk_aspects", []), list):
        errors.append("prompt_alignment matched_aspects and risk_aspects must be arrays")
    return not errors, errors


class ScorePatchValidationService:
    """Validate patch schema, target range, constraints, and exportability."""

    def __init__(self) -> None:
        self.musicxml_validator = MusicXMLValidator()

    def validate_patch(
        self,
        score_document: dict[str, Any],
        patch: dict[str, Any],
        instruction: str = "",
        selected_range: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a paper-facing ScorePatchValidationReport."""

        constraints = constraints or {}
        selected_range = selected_range or patch.get("target_range") or {"start_measure": 1, "end_measure": 1}
        schema_valid, schema_errors = validate_score_patch_schema(patch)
        target = patch.get("target_range") if isinstance(patch.get("target_range"), dict) else {}
        start = _safe_int(target.get("start_measure"), 1)
        end = _safe_int(target.get("end_measure"), start)
        measure_numbers = {int(measure.get("number", 0)) for measure in score_document.get("measures", [])}

        warnings: list[str] = []
        errors = list(schema_errors)
        structural_risks: list[str] = []
        constraint_violations: list[str] = []

        target_range_valid = schema_valid and start <= end and all(number in measure_numbers for number in range(start, end + 1))
        if not target_range_valid:
            errors.append("target_range does not exist in score_document")

        operations = list(patch.get("operations") or []) if isinstance(patch.get("operations"), list) else []
        for index, operation in enumerate(operations):
            op_start, op_end = _operation_measure_range(operation, start, end)
            if op_start is not None and (op_start < start or op_end > end):
                errors.append(f"operation {index} targets measures outside patch target_range")
            op_type = str(operation.get("type", ""))
            if op_type == "change_meter" and "meter" not in instruction.lower() and "拍" not in instruction:
                structural_risks.append("meter changes require explicit prompt support")
            if op_type == "change_key" and "key" not in instruction.lower() and "调" not in instruction:
                structural_risks.append("key changes require explicit prompt support")

        if constraints.get("preserve_harmony") and any(operation_changes_harmony(op) for op in operations):
            constraint_violations.append("preserve_harmony violated by harmony operation")
        if constraints.get("preserve_melody") and any(operation_changes_melody(op) for op in operations):
            constraint_violations.append("preserve_melody violated by melodic operation")
        if constraints.get("preserve_rhythm") and any(operation_changes_rhythm(op) for op in operations):
            constraint_violations.append("preserve_rhythm violated by rhythmic operation")

        patched_score: dict[str, Any] | None = None
        musicxml_valid = False
        try:
            patched_score, _ = apply_operations(score_document, operations)
            validation_report = self.musicxml_validator.validate_text(score_document_to_musicxml(patched_score)).to_report()
            musicxml_valid = bool(validation_report.get("valid_musicxml"))
            if not musicxml_valid:
                errors.append("patched score cannot be exported as valid MusicXML")
        except Exception as exc:  # noqa: BLE001 - report, do not crash preview.
            validation_report = {"valid_musicxml": False, "warnings": [], "errors": [str(exc)]}
            errors.append(f"patch application failed: {exc}")

        if patched_score is not None:
            empty_targets = [
                int(measure.get("number", 0))
                for measure in patched_score.get("measures", [])
                if start <= int(measure.get("number", 0)) <= end and not measure.get("events")
            ]
            if empty_targets:
                structural_risks.append(f"target measures without editable events: {empty_targets}")

        patch_size = len(operations)
        over_editing_risk = _over_editing_risk(patch_size, max(1, end - start + 1), constraints)
        if over_editing_risk == "high":
            warnings.append("patch size is high for the selected range")

        alignment = score_prompt_alignment(instruction, selected_range, constraints, patch, validation_report)
        if alignment.get("overall_prompt_alignment_edit_score", 1.0) < 0.55:
            warnings.append("prompt alignment score is low")

        valid = not errors and musicxml_valid and schema_valid
        recommendation = "reject" if not valid else "review" if constraint_violations or structural_risks or over_editing_risk == "high" else "accept"
        return {
            "patch_id": str(patch.get("patch_id", "")),
            "valid": bool(valid),
            "target_range_valid": bool(target_range_valid),
            "constraint_violations": constraint_violations,
            "structural_risks": sorted(set(structural_risks)),
            "musicxml_valid_after_patch": bool(musicxml_valid),
            "patch_size": patch_size,
            "over_editing_risk": over_editing_risk,
            "recommendation": recommendation,
            "warnings": warnings,
            "errors": sorted(set(errors)),
            "prompt_alignment_score": alignment,
        }


def _operation_measure_range(operation: dict[str, Any], fallback_start: int, fallback_end: int) -> tuple[int | None, int | None]:
    target = operation.get("target") or {}
    op_type = str(operation.get("type", ""))
    if op_type in GLOBAL_OPERATION_TYPES:
        return fallback_start, fallback_end
    start = target.get("start_measure") or target.get("measure") or target.get("measure_number")
    end = target.get("end_measure") or start
    if start is None and target.get("measure_id"):
        match = re.search(r"(\d+)", str(target.get("measure_id")))
        if match:
            start = match.group(1)
            end = start
    if start is None:
        return fallback_start, fallback_end
    return _safe_int(start, fallback_start), _safe_int(end, _safe_int(start, fallback_start))


def _over_editing_risk(patch_size: int, measure_count: int, constraints: dict[str, Any]) -> str:
    limit_name = str(constraints.get("patch_size_limit", "")).lower()
    threshold = {
        "small": max(2, measure_count * 2),
        "medium": max(4, measure_count * 4),
        "large": max(8, measure_count * 8),
    }.get(limit_name, max(8, measure_count * 6))
    if patch_size > threshold:
        return "high"
    if patch_size > max(2, int(threshold * 0.7)):
        return "medium"
    return "low"


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback

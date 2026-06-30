"""Preview, apply, partially apply, and reject ScorePatch payloads."""

from __future__ import annotations

import uuid
from typing import Any

from backend.services.prompt_alignment_service import score_prompt_alignment
from backend.services.score_document_service import score_document_to_musicxml
from backend.services.score_operation_service import apply_operations
from backend.services.score_patch_validation_service import ScorePatchValidationService
from backend.validation.musicxml_validator import MusicXMLValidator


class ScorePatchService:
    """Apply local ScorePatch operations with validation before acceptance."""

    def __init__(self) -> None:
        self.validator = MusicXMLValidator()
        self.patch_validator = ScorePatchValidationService()

    def normalize_patch(self, patch: dict[str, Any]) -> dict[str, Any]:
        """Fill required ScorePatch fields."""

        normalized = dict(patch or {})
        normalized.setdefault("patch_id", f"patch_{uuid.uuid4().hex[:12]}")
        normalized.setdefault("patch_type", "transform_notes")
        normalized.setdefault("target_range", {"start_measure": 1, "end_measure": 1})
        normalized.setdefault("operations", [])
        normalized.setdefault("rationale", "Local V0.6 score edit.")
        normalized.setdefault("expected_effect", "The selected passage changes while the rest of the score is preserved.")
        normalized.setdefault("prompt_alignment", {"instruction": "", "matched_aspects": [], "risk_aspects": []})
        normalized.setdefault(
            "validation_expectations",
            {
                "should_preserve_measure_count": True,
                "should_preserve_meter": True,
                "should_preserve_harmony": False,
            },
        )
        return normalized

    def preview_patch(
        self,
        score_document: dict[str, Any],
        patch: dict[str, Any],
        instruction: str = "",
        selected_range: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return before/after diff data without mutating the caller."""

        patch = self.normalize_patch(patch)
        updated, operations = apply_operations(score_document, list(patch.get("operations") or []))
        musicxml = score_document_to_musicxml(updated)
        validation = self.validator.validate_text(musicxml).to_report()
        selected_range = selected_range or patch["target_range"]
        constraints = constraints or {}
        alignment = score_prompt_alignment(instruction, selected_range, constraints, patch, validation)
        patch_validation = self.patch_validator.validate_patch(
            score_document,
            {**patch, "operations": operations},
            instruction=instruction,
            selected_range=selected_range,
            constraints=constraints,
        )
        return {
            "patch": {**patch, "operations": operations},
            "before_score_document": score_document,
            "after_score_document": updated,
            "validation_report": validation,
            "prompt_alignment_score": alignment,
            "patch_validation_report": patch_validation,
            "diff": self._diff_summary(score_document, updated, patch),
        }

    def apply_patch(
        self,
        score_document: dict[str, Any],
        patch: dict[str, Any],
        instruction: str = "",
        selected_range: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply a patch only if the resulting MusicXML remains valid."""

        preview = self.preview_patch(score_document, patch, instruction, selected_range, constraints)
        patch_report = preview.get("patch_validation_report", {})
        valid = bool(preview["validation_report"].get("valid_musicxml")) and bool(patch_report.get("valid", True))
        return {
            **preview,
            "accepted": valid,
            "rejected": not valid,
            "rejection_reason": "" if valid else "; ".join(patch_report.get("errors") or ["Patch result failed validation."]),
            "score_document": preview["after_score_document"] if valid else score_document,
        }

    def validate_patch(
        self,
        score_document: dict[str, Any],
        patch: dict[str, Any],
        instruction: str = "",
        selected_range: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate a patch without returning score diffs."""

        return self.patch_validator.validate_patch(
            score_document,
            self.normalize_patch(patch),
            instruction=instruction,
            selected_range=selected_range,
            constraints=constraints,
        )

    def partial_apply_patch(
        self,
        score_document: dict[str, Any],
        patch: dict[str, Any],
        operation_ids: list[str] | None = None,
        operation_indexes: list[int] | None = None,
        apply_filter: str = "selected",
        instruction: str = "",
        selected_range: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply a subset of patch operations and keep rejected ops for history."""

        patch = self.normalize_patch(patch)
        operations = list(patch.get("operations") or [])
        selected_operations = _select_partial_operations(operations, operation_ids, operation_indexes, apply_filter)
        selected_ids = {id(operation) for operation in selected_operations}
        rejected_operations = [operation for operation in operations if id(operation) not in selected_ids]
        partial_patch = {
            **patch,
            "patch_id": f"{patch['patch_id']}_partial",
            "operations": selected_operations,
            "rationale": f"Partial apply: {patch.get('rationale', '')}",
        }
        result = self.apply_patch(score_document, partial_patch, instruction, selected_range, constraints)
        result["partial"] = True
        result["rejected_operations"] = rejected_operations
        result["original_patch_id"] = patch.get("patch_id")
        return result

    def reject_patch(self, score_document: dict[str, Any], patch: dict[str, Any], reason: str = "") -> dict[str, Any]:
        """Record a rejected patch without changing the score."""

        patch = self.normalize_patch(patch)
        return {
            "patch": patch,
            "accepted": False,
            "rejected": True,
            "rejection_reason": reason or "User rejected patch preview.",
            "score_document": score_document,
        }

    @staticmethod
    def _diff_summary(before: dict[str, Any], after: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        target = patch.get("target_range") or {}
        start = int(target.get("start_measure", 1))
        end = int(target.get("end_measure", start))
        before_measures = [m for m in before.get("measures", []) if start <= int(m.get("number", 0)) <= end]
        after_measures = [m for m in after.get("measures", []) if start <= int(m.get("number", 0)) <= end]
        before_events = sum(len(m.get("events", [])) for m in before_measures)
        after_events = sum(len(m.get("events", [])) for m in after_measures)
        return {
            "target_range": {"start_measure": start, "end_measure": end},
            "before_event_count": before_events,
            "after_event_count": after_events,
            "operation_count": len(patch.get("operations") or []),
            "changed_measures": [m.get("number") for m in after_measures],
        }


def _select_partial_operations(
    operations: list[dict[str, Any]],
    operation_ids: list[str] | None,
    operation_indexes: list[int] | None,
    apply_filter: str,
) -> list[dict[str, Any]]:
    if operation_ids:
        wanted = set(operation_ids)
        return [operation for operation in operations if str(operation.get("operation_id", "")) in wanted]
    if operation_indexes:
        wanted_indexes = set(operation_indexes)
        return [operation for index, operation in enumerate(operations) if index in wanted_indexes]
    if apply_filter == "notes":
        return [operation for operation in operations if str(operation.get("type")) in {"insert_note", "delete_note", "update_pitch", "move_note", "transpose_selection"}]
    if apply_filter == "dynamics":
        return [operation for operation in operations if str(operation.get("type")) in {"change_dynamic"}]
    if apply_filter == "harmony":
        return [operation for operation in operations if str(operation.get("type")) in {"add_harmony_label", "update_harmony", "add_cadence"}]
    if apply_filter == "measures":
        return [operation for operation in operations if "measure" in str(operation.get("type")) or "start_measure" in operation.get("target", {})]
    return operations

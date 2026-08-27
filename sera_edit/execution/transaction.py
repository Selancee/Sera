"""Atomic validate-apply-roundtrip-commit ScorePatch transaction."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from backend.services.score_document_service import (
    musicxml_to_score_document,
    normalize_score_document,
    prepare_score_document_for_export,
    score_document_to_musicxml,
)
from backend.notation.beaming import materialize_beams_for_score_document
from backend.validation.musicxml_validator import MusicXMLValidator
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.domain.operations import OperationApplicationError, apply_patch_operation
from sera_edit.domain.score_patch import ScorePatch
from sera_edit.execution.diff_engine import score_diff
from sera_edit.execution.undo_manager import UndoManager
from sera_edit.validation.duration_validator import validate_measure_durations
from sera_edit.validation.notation_relation_validator import validate_notation_relations
from sera_edit.validation.protected_scope_validator import validate_protected_scope
from sera_edit.validation.roundtrip_fidelity_validator import validate_roundtrip_fidelity
from sera_edit.validation.schema_validator import validate_patch_schema
from sera_edit.validation.semantic_precondition_validator import validate_postconditions, validate_preconditions
from sera_edit.validation.structural_validator import validate_structure
from sera_edit.validation.validation_report import ValidationIssue, ValidationReport


@dataclass(slots=True)
class TransactionResult:
    """Serializable result of one transactional patch attempt."""

    committed: bool
    score_document: dict[str, Any]
    report: ValidationReport
    diff: dict[str, Any] = field(default_factory=dict)
    audit: list[dict[str, Any]] = field(default_factory=list)
    source_fingerprint: str = ""
    post_fingerprint: str = ""
    musicxml: str | None = None
    rollback_reason: str | None = None
    history_entry: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "committed": self.committed,
            "score_document": copy.deepcopy(self.score_document),
            "validation_report": self.report.as_dict(),
            "diff": copy.deepcopy(self.diff),
            "audit": copy.deepcopy(self.audit),
            "source_fingerprint": self.source_fingerprint,
            "post_fingerprint": self.post_fingerprint,
            "musicxml": self.musicxml,
            "rollback_reason": self.rollback_reason,
            "proposed_score_document": (
                copy.deepcopy(self.history_entry["after_score_document"])
                if self.history_entry is not None
                else None
            ),
        }


class PatchTransaction:
    """Execute ScorePatch with rollback on every failed validation layer."""

    def __init__(self, *, undo_manager: UndoManager | None = None) -> None:
        self.undo_manager = undo_manager
        self.musicxml_validator = MusicXMLValidator()

    def execute(
        self,
        score_document: dict[str, Any],
        patch_payload: dict[str, Any],
        *,
        dry_run: bool = False,
    ) -> TransactionResult:
        """Validate and atomically apply a patch, preserving caller-owned input."""

        before = normalize_score_document(score_document)
        source_fingerprint = score_fingerprint(before)
        report = validate_patch_schema(patch_payload)
        if report.errors:
            return self._rollback(before, report, source_fingerprint, "schema validation failed")
        try:
            patch = ScorePatch.from_dict(patch_payload)
        except (TypeError, ValueError) as exc:
            report.add_error(ValidationIssue("E04", str(exc), "schema", True))
            return self._rollback(before, report, source_fingerprint, "patch parsing failed")
        if patch.source_score_id != str(before.get("score_id", "")):
            report.add_error(ValidationIssue("E05", "source_score_id does not match the current score", "source"))
        if patch.source_fingerprint != source_fingerprint:
            report.add_error(
                ValidationIssue(
                    "E05",
                    "source_fingerprint does not match the current canonical score",
                    "source",
                    details={"expected": source_fingerprint, "received": patch.source_fingerprint},
                )
            )
        report.merge(validate_structure(before, patch), check_name="structural")
        report.merge(validate_preconditions(before, patch.preconditions), check_name="preconditions")
        if report.errors:
            return self._rollback(before, report, source_fingerprint, "pre-apply validation failed")

        working = copy.deepcopy(before)
        audit: list[dict[str, Any]] = []
        try:
            for operation in patch.operations:
                working, operation_audit = apply_patch_operation(working, operation, patch.target_scope)
                audit.append(operation_audit)
        except OperationApplicationError as exc:
            report.add_error(
                ValidationIssue(exc.code, exc.message, "apply", details=copy.deepcopy(exc.details or {}))
            )
            return self._rollback(before, report, source_fingerprint, "operation application failed", audit=audit)

        # Compare against the same beam-materialization baseline used for the
        # proposed score. Host-imported MusicXML keeps its authoritative beam
        # markup; Sera-owned scores may derive beams on both sides. This prevents
        # exporter-only beaming from appearing as an out-of-scope user edit.
        comparison_before = materialize_beams_for_score_document(before)
        working = materialize_beams_for_score_document(working)
        diff = score_diff(comparison_before, working)
        report.merge(validate_measure_durations(working), check_name="duration")
        report.merge(validate_notation_relations(working), check_name="notation_relations")
        report.merge(
            validate_protected_scope(comparison_before, working, patch.target_scope, patch.protected_scope),
            check_name="protected_scope",
        )
        report.merge(
            validate_postconditions(comparison_before, working, patch.expected_effects),
            check_name="postconditions",
        )
        musicxml: str | None = None
        try:
            musicxml = score_document_to_musicxml(working)
            ET.fromstring(musicxml)
            roundtrip = musicxml_to_score_document(musicxml, source="sera_edit_roundtrip")
            validation = self.musicxml_validator.validate_text(musicxml)
            report.checks["musicxml_roundtrip"] = {
                "exported": True,
                "reimported": bool(roundtrip.get("measures")),
                "validator_valid": validation.valid,
                "issues": list(validation.issues),
                "warnings": list(validation.warnings),
                "metrics": dict(validation.metrics),
            }
            report.merge(
                # MusicXML export deterministically materializes implicit rests
                # for sparse workbench measures.  Compare the re-import against
                # that exact export-domain score, while keeping ``working`` as
                # the authoritative sparse editing document returned to callers.
                validate_roundtrip_fidelity(prepare_score_document_for_export(working), roundtrip),
                check_name="roundtrip_fidelity",
            )
            if not validation.valid:
                report.add_error(
                    ValidationIssue(
                        "E02",
                        "post-patch MusicXML did not pass the repository validator",
                        "roundtrip",
                        details={"issues": list(validation.issues)},
                    )
                )
        except Exception as exc:  # noqa: BLE001 - parser adapters raise heterogeneous exceptions.
            report.add_error(ValidationIssue("E02", f"MusicXML round-trip failed: {exc}", "roundtrip"))
        if report.errors:
            return self._rollback(
                before,
                report,
                source_fingerprint,
                "post-apply validation failed",
                diff=diff,
                audit=audit,
                musicxml=musicxml,
            )

        post_fingerprint = score_fingerprint(working)
        history_entry = {
            "patch_id": patch.patch_id,
            "source_fingerprint": source_fingerprint,
            "post_fingerprint": post_fingerprint,
            "before_score_document": copy.deepcopy(before),
            "after_score_document": copy.deepcopy(working),
            "diff": copy.deepcopy(diff),
            "audit": copy.deepcopy(audit),
        }
        if not dry_run and self.undo_manager is not None:
            self.undo_manager.record(history_entry)
        return TransactionResult(
            committed=not dry_run,
            score_document=copy.deepcopy(before if dry_run else working),
            report=report,
            diff=diff,
            audit=audit,
            source_fingerprint=source_fingerprint,
            post_fingerprint=post_fingerprint,
            musicxml=musicxml,
            history_entry=history_entry,
        )

    @staticmethod
    def _rollback(
        before: dict[str, Any],
        report: ValidationReport,
        source_fingerprint: str,
        reason: str,
        *,
        diff: dict[str, Any] | None = None,
        audit: list[dict[str, Any]] | None = None,
        musicxml: str | None = None,
    ) -> TransactionResult:
        return TransactionResult(
            committed=False,
            score_document=copy.deepcopy(before),
            report=report,
            diff=copy.deepcopy(diff or {}),
            audit=copy.deepcopy(audit or []),
            source_fingerprint=source_fingerprint,
            post_fingerprint=source_fingerprint,
            musicxml=musicxml,
            rollback_reason=reason,
        )

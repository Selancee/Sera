"""Versioned SeraEdit ScorePatch domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from sera_edit.domain.score_scope import ScoreScope


SCHEMA_VERSION = "1.0.0"
SUPPORTED_OPERATION_TYPES = {
    "transpose",
    "set_pitch",
    "set_duration",
    "insert_note",
    "insert_rest",
    "delete_event",
    "set_dynamic",
    "set_articulation",
    "set_tie",
    "set_slur",
    "change_key_signature",
    "change_time_signature",
    "move_to_voice",
    "duplicate_motif",
    "replace_chord",
    "batch",
}


@dataclass(frozen=True, slots=True)
class PatchOperation:
    """One strict operation in a SeraEdit patch."""

    operation_id: str
    type: str
    selector: dict[str, Any]
    arguments: dict[str, Any]
    preconditions: tuple[dict[str, Any], ...] = ()
    expected_change_count: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PatchOperation":
        """Construct an immutable operation from JSON data."""

        return cls(
            operation_id=str(payload.get("operation_id", "")),
            type=str(payload.get("type", "")),
            selector=dict(payload.get("selector") or {}),
            arguments=dict(payload.get("arguments") or {}),
            preconditions=tuple(dict(item) for item in payload.get("preconditions") or []),
            expected_change_count=(
                None if payload.get("expected_change_count") is None else int(payload["expected_change_count"])
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable operation."""

        return {
            "operation_id": self.operation_id,
            "type": self.type,
            "selector": dict(self.selector),
            "arguments": dict(self.arguments),
            "preconditions": [dict(item) for item in self.preconditions],
            "expected_change_count": self.expected_change_count,
        }


@dataclass(frozen=True, slots=True)
class ScorePatch:
    """Strict, source-bound, scope-aware score patch."""

    schema_version: str
    patch_id: str
    source_score_id: str
    source_fingerprint: str
    instruction: str
    target_scope: ScoreScope
    protected_scope: ScoreScope
    operations: tuple[PatchOperation, ...]
    preconditions: tuple[dict[str, Any], ...] = ()
    expected_effects: tuple[dict[str, Any], ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ScorePatch":
        """Construct a patch after schema validation."""

        return cls(
            schema_version=str(payload.get("schema_version", "")),
            patch_id=str(payload.get("patch_id", "")),
            source_score_id=str(payload.get("source_score_id", "")),
            source_fingerprint=str(payload.get("source_fingerprint", "")),
            instruction=str(payload.get("instruction", "")),
            target_scope=ScoreScope.from_dict(payload.get("target_scope")),
            protected_scope=ScoreScope.from_dict(payload.get("protected_scope")),
            operations=tuple(PatchOperation.from_dict(item) for item in payload.get("operations") or []),
            preconditions=tuple(dict(item) for item in payload.get("preconditions") or []),
            expected_effects=tuple(dict(item) for item in payload.get("expected_effects") or []),
            provenance=dict(payload.get("provenance") or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the stable JSON representation."""

        return {
            "schema_version": self.schema_version,
            "patch_id": self.patch_id,
            "source_score_id": self.source_score_id,
            "source_fingerprint": self.source_fingerprint,
            "instruction": self.instruction,
            "target_scope": self.target_scope.as_dict(),
            "protected_scope": self.protected_scope.as_dict(),
            "preconditions": [dict(item) for item in self.preconditions],
            "operations": [operation.as_dict() for operation in self.operations],
            "expected_effects": [dict(item) for item in self.expected_effects],
            "provenance": dict(self.provenance),
        }

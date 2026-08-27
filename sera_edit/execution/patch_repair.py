"""Bounded deterministic repairs for common ScorePatch formatting faults."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from sera_edit.domain.score_patch import SCHEMA_VERSION
from sera_edit.validation.schema_validator import validate_patch_schema


@dataclass(frozen=True, slots=True)
class RepairResult:
    """Traceable result of one deterministic repair pass."""

    original: dict[str, Any]
    repaired: dict[str, Any]
    changes: tuple[str, ...]
    valid: bool


def deterministic_repair(payload: dict[str, Any]) -> RepairResult:
    """Apply only unambiguous normalization; never infer musical intent."""

    repaired = copy.deepcopy(payload)
    changes: list[str] = []
    if not repaired.get("schema_version"):
        repaired["schema_version"] = SCHEMA_VERSION
        changes.append("added schema_version")
    for name in ("target_scope", "protected_scope"):
        scope = repaired.get(name)
        if isinstance(scope, dict):
            for plural, singular in (("measures", "measure"), ("event_ids", "event_id")):
                if singular in scope and plural not in scope:
                    scope[plural] = [scope.pop(singular)]
                    changes.append(f"normalized {name}.{singular} to {plural}")
    for operation in repaired.get("operations") or []:
        if not isinstance(operation, dict):
            continue
        op_type = operation.get("type")
        if isinstance(op_type, str) and op_type.lower() != op_type:
            operation["type"] = op_type.lower()
            changes.append(f"normalized operation type {op_type}")
        selector = operation.get("selector")
        if isinstance(selector, dict):
            if "event_id" in selector and "event_ids" not in selector:
                selector["event_ids"] = [selector.pop("event_id")]
                changes.append("normalized selector.event_id to event_ids")
            if "measure" in selector and "measures" not in selector:
                selector["measures"] = [selector["measure"]]
                changes.append("added selector.measures")
    return RepairResult(
        original=copy.deepcopy(payload),
        repaired=repaired,
        changes=tuple(changes),
        valid=not validate_patch_schema(repaired).errors,
    )

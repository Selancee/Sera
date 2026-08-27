"""Strict ScorePatch operation execution over the canonical ScoreDocument."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from backend.services.score_document_service import normalize_score_document, transpose_pitch
from sera_edit.domain.score_patch import PatchOperation
from sera_edit.domain.score_scope import EventContext, ScoreScope, iter_event_contexts, normalize_staff


@dataclass(slots=True)
class OperationApplicationError(ValueError):
    """A deterministic operation failure with an evaluation error code."""

    code: str
    message: str
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


def _selector_scope(operation: PatchOperation, fallback: ScoreScope) -> ScoreScope:
    selector = dict(operation.selector)
    if "event_id" in selector and "event_ids" not in selector:
        selector["event_ids"] = [selector.pop("event_id")]
    if "measure" in selector and "measures" not in selector:
        selector["measures"] = [selector.pop("measure")]
    scope = ScoreScope.from_dict(selector)
    return fallback if scope.empty else scope


def _selected(score: dict[str, Any], operation: PatchOperation, fallback: ScoreScope) -> list[EventContext]:
    return _selector_scope(operation, fallback).select(score)


def _event_index(score: dict[str, Any]) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    return {
        str(event.get("event_id", "")): (measure, event)
        for measure in score.get("measures") or []
        for event in measure.get("events") or []
    }


def _measure(score: dict[str, Any], number: int) -> dict[str, Any]:
    for measure in score.get("measures") or []:
        if int(measure.get("number", 0)) == number:
            return measure
    raise OperationApplicationError("E05", f"measure {number} does not exist", {"measure": number})


def _require_selected(contexts: list[EventContext], operation: PatchOperation) -> None:
    if not contexts:
        raise OperationApplicationError(
            "E06",
            f"operation {operation.operation_id} selected no events",
            {"operation_id": operation.operation_id},
        )


def apply_patch_operation(
    score_document: dict[str, Any],
    operation: PatchOperation,
    target_scope: ScoreScope,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply one supported operation without mutating the caller's score."""

    score = copy.deepcopy(score_document)
    contexts = _selected(score, operation, target_scope)
    arguments = dict(operation.arguments)
    changed_ids: list[str] = []
    inserted_ids: list[str] = []
    deleted_ids: list[str] = []

    if operation.type == "transpose":
        _require_selected(contexts, operation)
        semitones = int(arguments["semitones"])
        for context in contexts:
            if context.event.get("type") == "note":
                context.event["pitch"] = transpose_pitch(str(context.event.get("pitch", "C4")), semitones)
                changed_ids.append(context.event_id)
    elif operation.type in {
        "set_pitch",
        "set_duration",
        "set_dynamic",
        "set_articulation",
        "set_tie",
        "set_slur",
        "move_to_voice",
    }:
        _require_selected(contexts, operation)
        field, argument = {
            "set_pitch": ("pitch", "pitch"),
            "set_duration": ("duration", "duration"),
            "set_dynamic": ("dynamic", "dynamic"),
            "set_articulation": ("articulations", "articulations"),
            "set_tie": ("tie", "tie"),
            "set_slur": ("slur", "slur"),
            "move_to_voice": ("voice", "voice"),
        }[operation.type]
        value = arguments[argument]
        if operation.type == "set_articulation" and isinstance(value, str):
            value = [value]
        for context in contexts:
            if operation.type == "set_pitch" and context.event.get("type") != "note":
                raise OperationApplicationError("E05", "set_pitch cannot target a rest")
            context.event[field] = copy.deepcopy(value)
            changed_ids.append(context.event_id)
    elif operation.type == "delete_event":
        _require_selected(contexts, operation)
        index = _event_index(score)
        for context in contexts:
            measure, event = index[context.event_id]
            measure["events"] = [item for item in measure.get("events", []) if item is not event]
            deleted_ids.append(context.event_id)
    elif operation.type in {"insert_note", "insert_rest"}:
        selector = dict(operation.selector)
        raw_measure = selector.get("measure") or (selector.get("measures") or [None])[0]
        if raw_measure is None:
            raise OperationApplicationError("E05", f"{operation.type} requires one target measure")
        measure = _measure(score, int(raw_measure))
        event_id = str(arguments.get("event_id") or f"{operation.operation_id}_event")
        if event_id in _event_index(score):
            raise OperationApplicationError("E05", f"event_id already exists: {event_id}")
        is_rest = operation.type == "insert_rest"
        event = {
            "event_id": event_id,
            "type": "rest" if is_rest else "note",
            "pitch": "" if is_rest else str(arguments["pitch"]),
            "duration": str(arguments.get("duration", "quarter")),
            "offset": float(arguments.get("offset", 0)),
            "voice": int(arguments.get("voice", 1)),
            "staff": normalize_staff(arguments.get("staff", "right_hand")),
            "tie": arguments.get("tie"),
            "slur": arguments.get("slur"),
            "accidental": str(arguments.get("accidental", "")),
            "dynamic": str(arguments.get("dynamic", "mf")),
            "articulations": list(arguments.get("articulations") or []),
            "grace": bool(arguments.get("grace", False)),
            "is_chord_tone": bool(arguments.get("is_chord_tone", False)),
            "chord_group_id": arguments.get("chord_group_id"),
            "selected": False,
        }
        measure.setdefault("events", []).append(event)
        inserted_ids.append(event_id)
    elif operation.type in {"change_key_signature", "change_time_signature"}:
        if not target_scope.whole_score:
            raise OperationApplicationError("E05", f"{operation.type} requires target_scope.whole_score=true")
        if operation.type == "change_key_signature":
            score.setdefault("global", {})["key"] = str(arguments["key"])
        else:
            score.setdefault("global", {})["meter"] = str(arguments["meter"])
    elif operation.type == "duplicate_motif":
        _require_selected(contexts, operation)
        target_measure = _measure(score, int(arguments["target_measure"]))
        offset_delta = float(arguments.get("offset_delta", 0))
        for index, context in enumerate(contexts, start=1):
            event = copy.deepcopy(context.event)
            event["event_id"] = f"{operation.operation_id}_dup_{index}"
            event["offset"] = float(event.get("offset", 0)) + offset_delta
            target_measure.setdefault("events", []).append(event)
            inserted_ids.append(event["event_id"])
    elif operation.type == "replace_chord":
        _require_selected(contexts, operation)
        pitches = [str(pitch) for pitch in arguments["pitches"]]
        if not pitches:
            raise OperationApplicationError("E04", "replace_chord requires at least one pitch")
        anchor = contexts[0]
        index = _event_index(score)
        for context in contexts:
            measure, event = index[context.event_id]
            measure["events"] = [item for item in measure.get("events", []) if item is not event]
            deleted_ids.append(context.event_id)
        target_measure = _measure(score, anchor.measure)
        chord_group_id = str(arguments.get("chord_group_id") or operation.operation_id)
        for position, pitch in enumerate(pitches, start=1):
            event = copy.deepcopy(anchor.event)
            event["event_id"] = f"{operation.operation_id}_chord_{position}"
            event["pitch"] = pitch
            event["type"] = "note"
            event["is_chord_tone"] = position > 1
            event["chord_group_id"] = chord_group_id
            target_measure.setdefault("events", []).append(event)
            inserted_ids.append(event["event_id"])
    elif operation.type == "batch":
        nested = arguments.get("operations") or []
        nested_audit: list[dict[str, Any]] = []
        for raw in nested:
            score, audit = apply_patch_operation(score, PatchOperation.from_dict(raw), target_scope)
            nested_audit.append(audit)
            changed_ids.extend(audit.get("changed_event_ids", []))
            inserted_ids.extend(audit.get("inserted_event_ids", []))
            deleted_ids.extend(audit.get("deleted_event_ids", []))
    else:
        raise OperationApplicationError("E19", f"unsupported operation type: {operation.type}")

    actual_change_count = len(set(changed_ids + inserted_ids + deleted_ids))
    if operation.expected_change_count is not None and actual_change_count != operation.expected_change_count:
        raise OperationApplicationError(
            "E15",
            f"operation {operation.operation_id} changed {actual_change_count} elements; expected {operation.expected_change_count}",
            {"actual": actual_change_count, "expected": operation.expected_change_count},
        )
    normalized = normalize_score_document(score)
    return normalized, {
        "operation_id": operation.operation_id,
        "type": operation.type,
        "changed_event_ids": sorted(set(changed_ids)),
        "inserted_event_ids": sorted(set(inserted_ids)),
        "deleted_event_ids": sorted(set(deleted_ids)),
        "actual_change_count": actual_change_count,
    }

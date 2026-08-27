"""ScoreOperation application and undo/redo helpers."""

from __future__ import annotations

import copy
import uuid
from typing import Any

from backend.services.score_document_service import normalize_score_document, transpose_pitch, utc_now


RHYTHM_OPERATION_TYPES = {"update_duration", "move_note", "quantize_rhythm", "simplify_rhythm", "humanize_rhythm"}
MELODY_OPERATION_TYPES = {"insert_note", "delete_note", "update_pitch", "transpose_selection", "add_cadence", "convert_rest_to_note", "convert_note_to_rest"}
HARMONY_OPERATION_TYPES = {"add_harmony_label", "update_harmony"}


def normalize_operation(operation: dict[str, Any]) -> dict[str, Any]:
    """Fill required ScoreOperation fields."""

    op = copy.deepcopy(operation or {})
    op.setdefault("operation_id", f"op_{uuid.uuid4().hex[:12]}")
    op.setdefault("timestamp", utc_now())
    op.setdefault("source", "user")
    op.setdefault("type", "no_op")
    op.setdefault("target", {})
    op.setdefault("before", {})
    op.setdefault("after", {})
    op.setdefault("description", op["type"].replace("_", " "))
    return op


def apply_score_operation(score: dict[str, Any], operation: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply one ScoreOperation and return the updated document plus audit op."""

    before_score = normalize_score_document(score)
    next_score = copy.deepcopy(before_score)
    op = normalize_operation(operation)
    op_type = str(op["type"])
    if op_type == "insert_note":
        _insert_event(next_score, op, event_type="note")
    elif op_type == "insert_rest":
        _insert_event(next_score, op, event_type="rest")
    elif op_type == "delete_note":
        _delete_event(next_score, op)
    elif op_type in {
        "update_pitch",
        "update_duration",
        "change_dynamic",
        "update_articulation",
        "update_tie",
        "update_staff",
        "update_voice",
        "move_to_staff",
        "change_voice",
        "move_note",
        "set_accidental",
        "convert_note_to_rest",
        "convert_rest_to_note",
        "add_slur",
        "remove_slur",
    }:
        _update_event(next_score, op)
    elif op_type == "transpose_selection":
        _transpose_selection(next_score, op)
    elif op_type == "duplicate_measure":
        _duplicate_measure(next_score, op)
    elif op_type == "delete_measure":
        _delete_measure(next_score, op)
    elif op_type == "insert_measure":
        _insert_measure(next_score, op)
    elif op_type == "change_key":
        next_score["global"]["key"] = str(op.get("after", {}).get("key", op.get("after", {}).get("value", "C major")))
    elif op_type == "change_meter":
        next_score["global"]["meter"] = str(op.get("after", {}).get("meter", op.get("after", {}).get("value", "4/4")))
    elif op_type == "change_tempo":
        next_score["global"]["tempo"] = int(op.get("after", {}).get("tempo", op.get("after", {}).get("value", 90)))
    elif op_type == "change_title":
        next_score["title"] = str(op.get("after", {}).get("title", op.get("after", {}).get("value", "")))
    elif op_type == "change_composer":
        next_score["composer"] = str(op.get("after", {}).get("composer", op.get("after", {}).get("value", "")))
    elif op_type in {"add_harmony_label", "update_harmony"}:
        _update_measure_field(next_score, op, "harmony")
    elif op_type == "add_section_label":
        _update_measure_field(next_score, op, "section")
    elif op_type == "add_cadence":
        _add_cadence(next_score, op)
    elif op_type == "simplify_rhythm":
        _rewrite_range_events(next_score, op, duration="quarter")
    elif op_type == "quantize_rhythm":
        _quantize_range(next_score, op)
    elif op_type == "humanize_rhythm":
        _rewrite_range_events(next_score, op, duration="eighth", every_other=True)
    elif op_type == "regenerate_selected_measures":
        _regenerate_selected_measures(next_score, op)
    else:
        op["description"] = op.get("description") or "no operation applied"
    next_score = normalize_score_document(next_score)
    op["before"] = {"score_document": before_score}
    op["after"] = {"score_document": next_score, **dict(op.get("after") or {})}
    return next_score, op


def apply_operations(score: dict[str, Any], operations: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Apply multiple operations in order."""

    current = normalize_score_document(score)
    audit: list[dict[str, Any]] = []
    for operation in operations:
        current, applied = apply_score_operation(current, operation)
        audit.append(applied)
    return current, audit


def undo_last(score: dict[str, Any], history: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Undo the latest applied operation using operation snapshots."""

    done = list(history.get("done", []))
    undone = list(history.get("undone", []))
    if not done:
        return normalize_score_document(score), {"done": done, "undone": undone}
    op = done.pop()
    previous = op.get("before", {}).get("score_document") or score
    undone.append(op)
    return normalize_score_document(previous), {"done": done, "undone": undone}


def redo_last(score: dict[str, Any], history: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Redo the most recently undone operation."""

    done = list(history.get("done", []))
    undone = list(history.get("undone", []))
    if not undone:
        return normalize_score_document(score), {"done": done, "undone": undone}
    op = undone.pop()
    updated = op.get("after", {}).get("score_document") or score
    done.append(op)
    return normalize_score_document(updated), {"done": done, "undone": undone}


def record_operation(history: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    """Append an operation and clear redo history."""

    done = list(history.get("done", []))
    done.append(operation)
    return {"done": done, "undone": []}


def replay_operations(score: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    """Replay operations from a base score."""

    return apply_operations(score, operations)[0]


def operation_changes_harmony(operation: dict[str, Any]) -> bool:
    return str(operation.get("type")) in HARMONY_OPERATION_TYPES


def operation_changes_melody(operation: dict[str, Any]) -> bool:
    return str(operation.get("type")) in MELODY_OPERATION_TYPES


def operation_changes_rhythm(operation: dict[str, Any]) -> bool:
    return str(operation.get("type")) in RHYTHM_OPERATION_TYPES


def _measure_by_id(score: dict[str, Any], measure_id: str | None = None, number: int | None = None) -> dict[str, Any]:
    measures = score.get("measures", [])
    for measure in measures:
        if measure_id and measure.get("measure_id") == measure_id:
            return measure
        if number is not None and int(measure.get("number", 0)) == number:
            return measure
    return measures[0]


def _target_measure(score: dict[str, Any], op: dict[str, Any]) -> dict[str, Any]:
    target = op.get("target", {})
    number = target.get("measure")
    if number is None:
        number = target.get("measure_number")
    return _measure_by_id(score, target.get("measure_id"), int(number) if number else None)


def _find_event(score: dict[str, Any], op: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    measure = _target_measure(score, op)
    event_id = op.get("target", {}).get("event_id")
    if event_id:
        for event in measure.get("events", []):
            if event.get("event_id") == event_id:
                return measure, event
    return measure, measure.get("events", [None])[0] if measure.get("events") else None


def _insert_event(score: dict[str, Any], op: dict[str, Any], event_type: str) -> None:
    measure = _target_measure(score, op)
    after = dict(op.get("after") or {})
    event = {
        "event_id": after.get("event_id", f"{measure['measure_id']}_e{uuid.uuid4().hex[:6]}"),
        "type": event_type,
        "pitch": "" if event_type == "rest" else after.get("pitch", "C4"),
        "duration": after.get("duration", "quarter"),
        "offset": float(after.get("offset", 0.0)),
        "voice": int(after.get("voice", 1)),
        "staff": after.get("staff", op.get("target", {}).get("staff", "right_hand")),
        "tie": after.get("tie"),
        "slur": after.get("slur"),
        "accidental": after.get("accidental", ""),
        "dynamic": after.get("dynamic", "mf"),
        "articulations": list(after.get("articulations", [])),
        "selected": False,
    }
    measure.setdefault("events", []).append(event)


def _delete_event(score: dict[str, Any], op: dict[str, Any]) -> None:
    measure, event = _find_event(score, op)
    if event is None:
        return
    measure["events"] = [item for item in measure.get("events", []) if item.get("event_id") != event.get("event_id")]


def _update_event(score: dict[str, Any], op: dict[str, Any]) -> None:
    _, event = _find_event(score, op)
    if event is None:
        return
    after = dict(op.get("after") or {})
    aliases = {
        "change_dynamic": "dynamic",
        "update_staff": "staff",
        "move_to_staff": "staff",
        "update_voice": "voice",
        "change_voice": "voice",
        "move_note": "offset",
        "set_accidental": "accidental",
    }
    op_type = str(op.get("type"))
    if op_type in aliases and "value" in after:
        after[aliases[op_type]] = after["value"]
    if op_type == "update_pitch" and "value" in after:
        after["pitch"] = after["value"]
    if op_type == "update_duration" and "value" in after:
        after["duration"] = after["value"]
    if op_type == "convert_note_to_rest":
        event["type"] = "rest"
        event["pitch"] = ""
    if op_type == "convert_rest_to_note":
        event["type"] = "note"
        event["pitch"] = after.get("pitch", "C4")
    if op_type == "add_slur":
        after["slur"] = after.get("slur", "start")
    if op_type == "remove_slur":
        after["slur"] = None
    if op_type == "set_accidental" and "accidental" in after:
        event["pitch"] = _apply_accidental(str(event.get("pitch", "C4")), str(after.get("accidental", "")))
    for key in ["pitch", "duration", "offset", "voice", "staff", "dynamic", "articulations", "tie", "slur", "accidental"]:
        if key in after:
            event[key] = after[key]


def _transpose_selection(score: dict[str, Any], op: dict[str, Any]) -> None:
    semitones = int(op.get("after", {}).get("semitones", op.get("after", {}).get("value", 0)))
    excluded = set(op.get("target", {}).get("exclude_event_ids") or [])
    for measure in _target_range(score, op):
        for event in measure.get("events", []):
            if event.get("type") == "note" and event.get("event_id") not in excluded:
                event["pitch"] = transpose_pitch(str(event.get("pitch", "C4")), semitones)


def _duplicate_measure(score: dict[str, Any], op: dict[str, Any]) -> None:
    measure = copy.deepcopy(_target_measure(score, op))
    measure["measure_id"] = f"m{uuid.uuid4().hex[:6]}"
    score["measures"].insert(int(measure.get("number", 1)), measure)
    _renumber_measures(score)


def _delete_measure(score: dict[str, Any], op: dict[str, Any]) -> None:
    target = _target_measure(score, op)
    score["measures"] = [measure for measure in score.get("measures", []) if measure.get("measure_id") != target.get("measure_id")]
    if not score["measures"]:
        score["measures"] = [target]
        score["measures"][0]["events"] = []
    _renumber_measures(score)


def _insert_measure(score: dict[str, Any], op: dict[str, Any]) -> None:
    after = dict(op.get("after") or {})
    measure = {
        "measure_id": after.get("measure_id", f"m{uuid.uuid4().hex[:6]}"),
        "number": int(after.get("number", len(score.get("measures", [])) + 1)),
        "section": after.get("section", "A"),
        "harmony": after.get("harmony", "I"),
        "cadence": after.get("cadence", "none"),
        "events": list(after.get("events", [])),
    }
    index = max(0, min(len(score.get("measures", [])), int(measure["number"]) - 1))
    score.setdefault("measures", []).insert(index, measure)
    _renumber_measures(score)


def _update_measure_field(score: dict[str, Any], op: dict[str, Any], field: str) -> None:
    measure = _target_measure(score, op)
    measure[field] = str(op.get("after", {}).get(field, op.get("after", {}).get("value", measure.get(field, ""))))


def _add_cadence(score: dict[str, Any], op: dict[str, Any]) -> None:
    measure = _target_range(score, op)[-1]
    measure["cadence"] = "authentic"
    measure["harmony"] = "I" if "minor" not in str(score.get("global", {}).get("key", "")).lower() else "i"
    right = [event for event in measure.get("events", []) if event.get("type") == "note" and event.get("staff") != "left_hand"]
    if len(right) >= 2:
        right[-2]["pitch"] = "G4"
        right[-1]["pitch"] = "C5"
    elif right:
        right[-1]["pitch"] = "C5"
    else:
        measure.setdefault("events", []).append(
            {"event_id": f"{measure['measure_id']}_cad", "type": "note", "pitch": "C5", "duration": "half", "offset": 2.0, "voice": 1, "staff": "right_hand", "tie": None, "dynamic": "mf", "articulations": [], "selected": False}
        )


def _rewrite_range_events(score: dict[str, Any], op: dict[str, Any], duration: str, every_other: bool = False) -> None:
    for measure in _target_range(score, op):
        for index, event in enumerate(measure.get("events", [])):
            if event.get("event_id") in set(op.get("target", {}).get("exclude_event_ids") or []):
                continue
            if every_other and index % 2:
                continue
            event["duration"] = duration


def _quantize_range(score: dict[str, Any], op: dict[str, Any]) -> None:
    for measure in _target_range(score, op):
        for event in measure.get("events", []):
            if event.get("event_id") in set(op.get("target", {}).get("exclude_event_ids") or []):
                continue
            event["offset"] = round(float(event.get("offset", 0.0)) * 2) / 2


def _regenerate_selected_measures(score: dict[str, Any], op: dict[str, Any]) -> None:
    generated = op.get("after", {}).get("measures")
    if not generated:
        _transpose_selection(score, {"target": op.get("target", {}), "after": {"semitones": 2}})
        return
    replacements = {int(item.get("number", 0)): item for item in generated}
    for index, measure in enumerate(score.get("measures", [])):
        if int(measure.get("number", 0)) in replacements:
            score["measures"][index] = replacements[int(measure.get("number", 0))]


def _target_range(score: dict[str, Any], op: dict[str, Any]) -> list[dict[str, Any]]:
    target = op.get("target", {})
    start = int(target.get("start_measure", target.get("measure", target.get("measure_number", 1))))
    end = int(target.get("end_measure", start))
    return [measure for measure in score.get("measures", []) if start <= int(measure.get("number", 0)) <= end] or [score["measures"][0]]


def _renumber_measures(score: dict[str, Any]) -> None:
    for number, measure in enumerate(score.get("measures", []), start=1):
        measure["number"] = number
        measure["measure_id"] = f"m{number}"


def _apply_accidental(pitch: str, accidental: str) -> str:
    import re

    match = re.match(r"^([A-G])([#b]?)(-?\d+)$", pitch)
    if not match:
        return pitch
    sign = "#" if accidental == "sharp" else "b" if accidental == "flat" else ""
    return f"{match.group(1)}{sign}{match.group(3)}"

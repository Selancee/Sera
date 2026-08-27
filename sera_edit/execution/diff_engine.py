"""Event-level deterministic ScoreDocument diffing."""

from __future__ import annotations

from typing import Any

from sera_edit.domain.score_scope import iter_event_contexts


IGNORED_EVENT_FIELDS = {"selected", "hovered", "layout", "render_bbox", "beam_group"}


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key not in IGNORED_EVENT_FIELDS}


def _global_value(field: str, value: Any) -> Any:
    if field == "key":
        return (
            str(value or "")
            .strip()
            .lower()
            .replace("-flat", "b")
            .replace(" flat", "b")
            .replace("-sharp", "#")
            .replace(" sharp", "#")
        )
    return value


def score_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Return added, deleted, changed, moved, and global score changes."""

    before_index = {context.event_id: context for context in iter_event_contexts(before)}
    after_index = {context.event_id: context for context in iter_event_contexts(after)}
    before_ids = set(before_index)
    after_ids = set(after_index)
    added = [after_index[event_id].location() | {"after": _event_payload(after_index[event_id].event)} for event_id in sorted(after_ids - before_ids)]
    deleted = [before_index[event_id].location() | {"before": _event_payload(before_index[event_id].event)} for event_id in sorted(before_ids - after_ids)]
    changed: list[dict[str, Any]] = []
    for event_id in sorted(before_ids & after_ids):
        old = before_index[event_id]
        new = after_index[event_id]
        fields = sorted(
            key
            for key in set(_event_payload(old.event)) | set(_event_payload(new.event))
            if _event_payload(old.event).get(key) != _event_payload(new.event).get(key)
        )
        moved = (old.measure, old.part_id, old.staff, old.voice, old.offset) != (
            new.measure,
            new.part_id,
            new.staff,
            new.voice,
            new.offset,
        )
        if fields or moved:
            changed.append(
                {
                    "event_id": event_id,
                    "before_location": old.location(),
                    "after_location": new.location(),
                    "changed_fields": fields,
                    "before": _event_payload(old.event),
                    "after": _event_payload(new.event),
                }
            )
    global_changes = {
        key: {"before": (before.get("global") or {}).get(key), "after": (after.get("global") or {}).get(key)}
        for key in sorted(set(before.get("global") or {}) | set(after.get("global") or {}))
        if _global_value(key, (before.get("global") or {}).get(key))
        != _global_value(key, (after.get("global") or {}).get(key))
    }
    return {
        "added": added,
        "deleted": deleted,
        "changed": changed,
        "global_changes": global_changes,
        "changed_element_count": len(added) + len(deleted) + len(changed) + len(global_changes),
    }

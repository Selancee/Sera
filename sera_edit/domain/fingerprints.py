"""Canonical semantic fingerprints for source-drift detection."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any


VOLATILE_METADATA_FIELDS = {
    "created_at",
    "updated_at",
    "last_opened_at",
    "notation_normalized",
    "notation_normalization_report",
    "beaming_assigned",
}
VOLATILE_EVENT_FIELDS = {"selected", "hovered", "layout", "render_bbox", "beam_group"}
SEMANTIC_DEFAULT_EVENT_FIELDS = {
    "grace": False,
    "is_chord_tone": False,
    "chord_group_id": None,
}


def _canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float):
        return str(Fraction(str(value)))
    return value


def _canonical_global(global_info: dict[str, Any]) -> dict[str, Any]:
    result = dict(global_info)
    if "key" in result:
        result["key"] = (
            str(result["key"] or "")
            .strip()
            .lower()
            .replace("-flat", "b")
            .replace(" flat", "b")
            .replace("-sharp", "#")
            .replace(" sharp", "#")
        )
    return result


def canonical_score_payload(score_document: dict[str, Any]) -> dict[str, Any]:
    """Return a stable semantic projection of ScoreDocument."""

    metadata = {
        key: value
        for key, value in dict(score_document.get("metadata") or {}).items()
        if key not in VOLATILE_METADATA_FIELDS
    }
    measures: list[dict[str, Any]] = []
    for measure in sorted(score_document.get("measures") or [], key=lambda item: int(item.get("number", 0))):
        events = []
        for event in sorted(
            measure.get("events") or [],
            key=lambda item: (
                Fraction(str(item.get("offset", 0))),
                str(item.get("staff", "")),
                int(item.get("voice", 1) or 1),
                str(item.get("event_id", "")),
            ),
        ):
            events.append(
                {
                    key: value
                    for key, value in event.items()
                    if key not in VOLATILE_EVENT_FIELDS
                    and not (key in SEMANTIC_DEFAULT_EVENT_FIELDS and value == SEMANTIC_DEFAULT_EVENT_FIELDS[key])
                }
            )
        measures.append(
            {
                "measure_id": measure.get("measure_id"),
                "number": measure.get("number"),
                "section": measure.get("section"),
                "harmony": measure.get("harmony"),
                "cadence": measure.get("cadence"),
                "events": events,
            }
        )
    return _canonical_value(
        {
            "schema_version": score_document.get("schema_version"),
            "score_id": score_document.get("score_id"),
            "title": score_document.get("title"),
            "composer": score_document.get("composer"),
            "metadata": metadata,
            "global": _canonical_global(score_document.get("global") or {}),
            "parts": score_document.get("parts") or [],
            "tracks": score_document.get("tracks") or [],
            "measures": measures,
            "annotations": score_document.get("annotations") or [],
        }
    )


def score_fingerprint(score_document: dict[str, Any]) -> str:
    """Return a prefixed SHA-256 fingerprint of canonical score semantics."""

    encoded = json.dumps(
        canonical_score_payload(score_document),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

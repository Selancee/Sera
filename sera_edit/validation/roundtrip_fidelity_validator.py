"""Semantic ScoreDocument fidelity checks after MusicXML export and re-import."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from sera_edit.domain.score_scope import EventContext, iter_event_contexts
from sera_edit.validation.duration_validator import duration_fraction
from sera_edit.validation.validation_report import ValidationIssue, ValidationReport


def _offset(value: object) -> Fraction:
    return Fraction(str(value or 0)).limit_denominator(96)


def _articulations(value: object) -> tuple[str, ...]:
    return tuple(sorted(str(item).strip().lower().replace("_", "-") for item in (value or [])))


def _accidental(value: object) -> str:
    aliases = {"#": "sharp", "b": "flat", "##": "double-sharp", "bb": "flat-flat"}
    clean = str(value or "").strip().lower().replace("_", "-")
    return aliases.get(clean, clean)


def _beam(value: object) -> tuple[int, str] | None:
    if not isinstance(value, dict) or not value:
        return None
    return int(value.get("number", 1)), str(value.get("value", "")).strip().lower()


def _key(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-flat", "b")
        .replace(" flat", "b")
        .replace("-sharp", "#")
        .replace(" sharp", "#")
    )


def _chord_peers(index: dict[str, EventContext], event_id: str) -> set[str]:
    context = index[event_id]
    return {
        other.event_id
        for other in index.values()
        if other.measure == context.measure
        and other.staff == context.staff
        and other.voice == context.voice
        and other.offset == context.offset
        and not other.event.get("grace")
        and other.event.get("type") != "rest"
    }


def validate_roundtrip_fidelity(
    source_score: dict[str, Any],
    imported_score: dict[str, Any],
) -> ValidationReport:
    """Require all source events and supported notation fields to survive."""

    report = ValidationReport()
    source = {context.event_id: context for context in iter_event_contexts(source_score)}
    imported = {context.event_id: context for context in iter_event_contexts(imported_score)}
    missing = sorted(set(source) - set(imported))
    added = sorted(set(imported) - set(source))
    mismatches: list[dict[str, Any]] = []
    global_mismatches: list[str] = []
    source_global = source_score.get("global") or {}
    imported_global = imported_score.get("global") or {}
    if _key(source_global.get("key")) != _key(imported_global.get("key")):
        global_mismatches.append("key")
    if str(source_global.get("meter", "4/4")) != str(imported_global.get("meter", "4/4")):
        global_mismatches.append("meter")
    if int(source_global.get("tempo", 90)) != int(imported_global.get("tempo", 90)):
        global_mismatches.append("tempo")
    for event_id in sorted(set(source) & set(imported)):
        old = source[event_id]
        new = imported[event_id]
        fields: list[str] = []
        if old.event.get("type") != new.event.get("type"):
            fields.append("type")
        if str(old.event.get("pitch", "")) != str(new.event.get("pitch", "")):
            fields.append("pitch")
        try:
            if duration_fraction(old.event.get("duration", "quarter")) != duration_fraction(
                new.event.get("duration", "quarter")
            ):
                fields.append("duration")
        except ValueError:
            fields.append("duration")
        if old.measure != new.measure or old.staff != new.staff or old.voice != new.voice or _offset(old.offset) != _offset(new.offset):
            fields.append("location")
        for field in ("tie", "slur", "dynamic"):
            if (old.event.get(field) or None) != (new.event.get(field) or None):
                fields.append(field)
        if _accidental(old.event.get("accidental")) != _accidental(new.event.get("accidental")):
            fields.append("accidental")
        if _articulations(old.event.get("articulations")) != _articulations(new.event.get("articulations")):
            fields.append("articulations")
        if _beam(old.event.get("beam")) != _beam(new.event.get("beam")):
            fields.append("beam")
        if bool(old.event.get("grace")) != bool(new.event.get("grace")):
            fields.append("grace")
        if _chord_peers(source, event_id) != _chord_peers(imported, event_id):
            fields.append("chord_membership")
        if fields:
            mismatches.append({"event_id": event_id, "fields": sorted(set(fields))})
    for event_id in missing:
        report.add_error(
            ValidationIssue("E14", f"event missing after MusicXML round-trip: {event_id}", "roundtrip_fidelity")
        )
    for event_id in added:
        report.add_error(
            ValidationIssue(
                "E14",
                f"unexpected event added during MusicXML round-trip: {event_id}",
                "roundtrip_fidelity",
            )
        )
    for details in mismatches:
        report.add_error(
            ValidationIssue(
                "E14",
                f"notation fields changed during MusicXML round-trip: {details['event_id']}",
                "roundtrip_fidelity",
                details=details,
            )
        )
    if global_mismatches:
        report.add_error(
            ValidationIssue(
                "E14",
                "global notation fields changed during MusicXML round-trip",
                "roundtrip_fidelity",
                details={"fields": global_mismatches},
            )
        )
    report.checks.update(
        {
            "source_event_count": len(source),
            "imported_event_count": len(imported),
            "missing_event_ids": missing,
            "added_event_ids": added,
            "field_mismatches": mismatches,
            "global_mismatches": global_mismatches,
            "fidelity_rate": 1.0
            - (len(missing) + len(added) + len(mismatches) + len(global_mismatches)) / max(1, len(source)),
        }
    )
    return report

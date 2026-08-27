"""Tie and slur relation integrity checks."""

from __future__ import annotations

from typing import Any

from sera_edit.domain.score_scope import iter_event_contexts
from sera_edit.validation.validation_report import ValidationIssue, ValidationReport


def validate_notation_relations(score: dict[str, Any]) -> ValidationReport:
    """Reject broken relations, malformed chords, and duplicate event IDs."""

    report = ValidationReport()
    open_ties: dict[tuple[str, int, str], str] = {}
    open_slurs: dict[tuple[str, int], str] = {}
    contexts = list(iter_event_contexts(score))
    event_ids = [context.event_id for context in contexts]
    for event_id in sorted({value for value in event_ids if event_ids.count(value) > 1}):
        report.add_error(ValidationIssue("E05", f"duplicate event_id: {event_id}", "notation"))
    chord_groups: dict[tuple[int, str, int, object], list[Any]] = {}
    for context in contexts:
        if not context.event.get("grace"):
            chord_key = (context.measure, context.staff, context.voice, context.offset)
            chord_groups.setdefault(chord_key, []).append(context)
        tie = context.event.get("tie")
        tie_key = (context.staff, context.voice, str(context.event.get("pitch", "")))
        if tie not in {None, "", "start", "stop", "continue"}:
            report.add_error(ValidationIssue("E09", f"invalid tie value {tie} at {context.event_id}", "notation"))
        if tie and (context.event.get("type") == "rest" or context.event.get("grace")):
            report.add_error(ValidationIssue("E09", f"tie cannot target rest/grace event {context.event_id}", "notation"))
        if tie in {"stop", "continue"} and tie_key not in open_ties:
            report.add_error(ValidationIssue("E09", f"tie stop without start at {context.event_id}", "notation"))
        if tie in {"start", "continue"}:
            open_ties[tie_key] = context.event_id
        elif tie == "stop":
            open_ties.pop(tie_key, None)
        slur = context.event.get("slur")
        slur_key = (context.staff, context.voice)
        if slur not in {None, "", "start", "stop", "continue"}:
            report.add_error(ValidationIssue("E10", f"invalid slur value {slur} at {context.event_id}", "notation"))
        if slur in {"stop", "continue"} and slur_key not in open_slurs:
            report.add_error(ValidationIssue("E10", f"slur stop without start at {context.event_id}", "notation"))
        if slur == "start" and slur_key in open_slurs:
            report.add_error(
                ValidationIssue(
                    "E10",
                    f"overlapping unnamed slur at {context.event_id}; numbered/nested slurs are not yet supported",
                    "notation",
                )
            )
        if slur in {"start", "continue"}:
            open_slurs[slur_key] = context.event_id
        elif slur == "stop":
            open_slurs.pop(slur_key, None)
    malformed_chords: list[dict[str, Any]] = []
    for (measure, staff, voice, offset), group in sorted(chord_groups.items()):
        explicit = [context for context in group if context.event.get("is_chord_tone") or context.event.get("chord_group_id")]
        if len(group) == 1 and explicit:
            malformed_chords.append(
                {"measure": measure, "staff": staff, "voice": voice, "offset": str(offset), "reason": "dangling_chord_member"}
            )
            continue
        if len(group) < 2:
            continue
        reasons: list[str] = []
        if any(context.event.get("type") == "rest" for context in group):
            reasons.append("rest_mixed_with_chord")
        durations = {str(context.event.get("duration", "quarter")) for context in group if not context.event.get("grace")}
        if len(durations) > 1:
            reasons.append("unequal_chord_durations")
        group_ids = {str(context.event.get("chord_group_id")) for context in group if context.event.get("chord_group_id")}
        if len(group_ids) > 1:
            reasons.append("conflicting_chord_group_ids")
        primary_count = sum(1 for context in group if not context.event.get("is_chord_tone"))
        if primary_count != 1:
            reasons.append("chord_requires_one_primary_note")
        if reasons:
            malformed_chords.append(
                {
                    "measure": measure,
                    "staff": staff,
                    "voice": voice,
                    "offset": str(offset),
                    "event_ids": [context.event_id for context in group],
                    "reasons": reasons,
                }
            )
    for details in malformed_chords:
        report.add_error(ValidationIssue("E08", "malformed chord membership", "notation", details=details))
    for (staff, voice, pitch), event_id in sorted(open_ties.items()):
        report.add_error(
            ValidationIssue(
                "E09",
                f"unclosed tie for {pitch} on {staff} voice {voice}",
                "notation",
                details={"start_event_id": event_id},
            )
        )
    for (staff, voice), event_id in sorted(open_slurs.items()):
        report.add_error(
            ValidationIssue(
                "E10",
                f"unclosed slur on {staff} voice {voice}",
                "notation",
                details={"start_event_id": event_id},
            )
        )
    report.checks.update(
        {
            "open_ties": len(open_ties),
            "open_slurs": len(open_slurs),
            "chord_onsets_checked": sum(1 for group in chord_groups.values() if len(group) > 1),
            "malformed_chords": malformed_chords,
            "event_ids_unique": len(event_ids) == len(set(event_ids)),
        }
    )
    return report

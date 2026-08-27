"""Normalize ScoreDocument notation grammar before export."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from backend.notation.beaming_rules import annotate_beam_groups
from backend.notation.duration_math import duration_to_fraction, fraction_to_float, fraction_to_duration_options
from backend.notation.meter_rules import measure_capacity_beats
from backend.notation.rest_grouping import grouped_rests_for_gap
from backend.notation.tie_splitter import split_event_at_barline


@dataclass(slots=True)
class NormalizationResult:
    score_document: dict[str, Any]
    changed: bool
    operations: list[dict[str, Any]]
    warnings: list[str]
    errors: list[str]
    report: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_document": self.score_document,
            "changed": self.changed,
            "operations": self.operations,
            "warnings": self.warnings,
            "errors": self.errors,
            "report": self.report,
        }


def normalize_score_document(score_document: dict[str, Any], options: dict[str, Any] | None = None) -> NormalizationResult:
    """Return a ScoreDocument whose measures fit meter capacity."""

    _ = options or {}
    score = copy.deepcopy(score_document or {})
    meter = str(score.get("global", {}).get("meter", "4/4"))
    capacity = measure_capacity_beats(meter)
    operations: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    report = {
        "measures_checked": 0,
        "duration_fixes": 0,
        "rest_grouping_fixes": 0,
        "tie_splits": 0,
        "beaming_fixes": 0,
        "overflow_fixes": 0,
    }

    measures = list(score.get("measures") or [])
    overflow_by_measure: dict[int, list[dict[str, Any]]] = {}
    for index, measure in enumerate(measures):
        report["measures_checked"] += 1
        measure.setdefault("measure_id", f"m{index + 1}")
        measure.setdefault("number", index + 1)
        measure.setdefault("section", "A")
        measure.setdefault("harmony", "I")
        measure.setdefault("cadence", "none")
        incoming = overflow_by_measure.pop(index, [])
        if incoming:
            measure.setdefault("events", []).extend(incoming)
            report["overflow_fixes"] += len(incoming)

        events = list(measure.get("events") or [])
        if not events:
            events = grouped_rests_for_gap(str(measure["measure_id"]), "right_hand", 1, Fraction(0, 1), capacity, meter)
            operations.append({"type": "fill_empty_measure", "measure": measure["number"]})
            report["rest_grouping_fixes"] += len(events)

        by_group: dict[tuple[str, int], list[dict[str, Any]]] = {}
        for event in events:
            staff = str(event.get("staff", "right_hand"))
            voice = int(event.get("voice", 1) or 1)
            by_group.setdefault((staff, voice), []).append(_normalized_event_defaults(event, measure["measure_id"]))

        normalized_events: list[dict[str, Any]] = []
        for (staff, voice), group_events in sorted(by_group.items()):
            cursor = Fraction(0, 1)
            for event in sorted(group_events, key=lambda item: (_exact_offset(item.get("offset", 0)), str(item.get("event_id", "")))):
                start = max(Fraction(0, 1), _exact_offset(event.get("offset", 0)))
                if event.get("grace"):
                    event["offset"] = fraction_to_float(start)
                    normalized_events.append(event)
                    continue
                duration = duration_to_fraction(str(event.get("duration", "quarter")))
                if duration <= 0:
                    duration = Fraction(1, 1)
                    event["duration"] = "quarter"
                    report["duration_fixes"] += 1
                if start > cursor:
                    rests = grouped_rests_for_gap(str(measure["measure_id"]), staff, voice, cursor, min(start, capacity), meter)
                    normalized_events.extend(rests)
                    report["rest_grouping_fixes"] += len(rests)
                    cursor = start
                if start >= capacity:
                    overflow = copy.deepcopy(event)
                    overflow["offset"] = fraction_to_float(start - capacity)
                    overflow_by_measure.setdefault(index + 1, []).append(overflow)
                    report["overflow_fixes"] += 1
                    continue
                kept, overflow = split_event_at_barline(event, start, duration, meter)
                normalized_events.append(kept)
                if overflow:
                    overflow_by_measure.setdefault(index + 1, []).extend(overflow)
                    operations.append({"type": "split_tie_overflow", "measure": measure["number"], "event_id": event.get("event_id")})
                    report["tie_splits"] += len(overflow)
                cursor = max(cursor, min(capacity, start + duration))
            if cursor < capacity:
                rests = grouped_rests_for_gap(str(measure["measure_id"]), staff, voice, cursor, capacity, meter)
                normalized_events.extend(rests)
                report["rest_grouping_fixes"] += len(rests)
        measure["events"] = annotate_beam_groups(sorted(normalized_events, key=lambda item: (str(item.get("staff")), float(item.get("offset", 0)), int(item.get("voice", 1)))), meter)
        report["beaming_fixes"] += sum(1 for event in measure["events"] if event.get("beam_group"))

    while overflow_by_measure:
        next_index = min(overflow_by_measure)
        incoming = overflow_by_measure.pop(next_index)
        new_number = next_index + 1
        new_measure = {
            "measure_id": f"m{new_number}",
            "number": new_number,
            "section": "overflow",
            "harmony": measures[-1].get("harmony", "I") if measures else "I",
            "cadence": "none",
            "events": incoming,
        }
        measures.append(new_measure)
        operations.append({"type": "append_overflow_measure", "measure": new_number})
        report["overflow_fixes"] += len(incoming)
        # Re-run only the appended measure through the main loop on the next call.
        recursive = normalize_score_document({**score, "measures": measures}, options)
        recursive.operations.insert(0, {"type": "append_overflow_measure", "measure": new_number})
        return recursive

    score["measures"] = measures
    score.setdefault("metadata", {})
    score["metadata"]["notation_normalized"] = True
    score["metadata"]["notation_normalization_report"] = report
    changed = bool(operations or report["rest_grouping_fixes"] or report["tie_splits"] or report["overflow_fixes"])
    return NormalizationResult(score, changed, operations, warnings, errors, report)


def _normalized_event_defaults(event: dict[str, Any], measure_id: str) -> dict[str, Any]:
    clone = copy.deepcopy(event)
    clone.setdefault("event_id", f"{measure_id}_event")
    clone.setdefault("type", "note")
    clone.setdefault("pitch", "" if clone.get("type") == "rest" else "C4")
    clone.setdefault("duration", "quarter")
    clone.setdefault("offset", 0.0)
    clone.setdefault("voice", 1)
    clone.setdefault("staff", "right_hand")
    clone.setdefault("tie", None)
    clone.setdefault("slur", None)
    clone.setdefault("accidental", "")
    clone.setdefault("dynamic", "mf")
    clone.setdefault("articulations", [])
    clone.setdefault("grace", False)
    clone.setdefault("is_chord_tone", False)
    clone.setdefault("chord_group_id", None)
    clone.setdefault("selected", False)
    if duration_to_fraction(str(clone.get("duration"))) not in {duration_to_fraction(label) for label in fraction_to_duration_options(duration_to_fraction(str(clone.get("duration"))))}:
        clone["duration"] = "quarter"
    return clone


def _exact_offset(value: object) -> Fraction:
    """Recover common notation fractions from legacy float offsets."""

    raw = Fraction(str(value or 0))
    limited = raw.limit_denominator(96)
    if abs(float(raw - limited)) <= 1e-5:
        return limited
    return raw

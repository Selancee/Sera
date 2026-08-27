"""Exact-rational measure duration validation."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from backend.notation.duration_math import DURATION_TO_FRACTION
from sera_edit.validation.validation_report import ValidationIssue, ValidationReport


def duration_fraction(label: object) -> Fraction:
    """Map a ScoreDocument duration label to exact quarter-note units."""

    name = str(label).strip().replace("-", "_")
    if name not in DURATION_TO_FRACTION:
        raise ValueError(f"unsupported duration label: {name}")
    return DURATION_TO_FRACTION[name]


def meter_quarters(meter: object) -> Fraction:
    """Return exact quarter-note capacity for a meter string."""

    try:
        beats, beat_type = (int(value) for value in str(meter).split("/", maxsplit=1))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid meter: {meter}") from exc
    if beats <= 0 or beat_type <= 0:
        raise ValueError(f"invalid meter: {meter}")
    return Fraction(beats * 4, beat_type)


def validate_measure_durations(score: dict[str, Any]) -> ValidationReport:
    """Reject overflow and report underfull voices without float comparisons."""

    report = ValidationReport()
    try:
        expected = meter_quarters((score.get("global") or {}).get("meter", "4/4"))
    except ValueError as exc:
        report.add_error(ValidationIssue("E07", str(exc), "duration"))
        return report
    totals: dict[str, str] = {}
    coverage: dict[str, dict[str, Any]] = {}
    pickup = bool((score.get("global") or {}).get("pickup", False))
    for measure_index, measure in enumerate(score.get("measures") or []):
        per_voice: dict[tuple[str, int], list[tuple[Fraction, Fraction, str]]] = {}
        for event in measure.get("events") or []:
            if event.get("grace"):
                continue
            try:
                start = Fraction(str(event.get("offset", 0)))
                end = start + duration_fraction(event.get("duration", "quarter"))
            except (ValueError, ZeroDivisionError) as exc:
                report.add_error(
                    ValidationIssue("E07", str(exc), "duration", details={"event_id": event.get("event_id")})
                )
                continue
            key = (str(event.get("staff", "right_hand")), int(event.get("voice", 1) or 1))
            per_voice.setdefault(key, []).append((start, end, str(event.get("event_id", ""))))
        for (staff, voice), raw_intervals in sorted(per_voice.items()):
            location = f"m{measure.get('number')}:{staff}:v{voice}"
            by_span: dict[tuple[Fraction, Fraction], list[str]] = {}
            for start, end, event_id in raw_intervals:
                by_span.setdefault((start, end), []).append(event_id)
            intervals = sorted(by_span)
            merged: list[list[Fraction]] = []
            collision_details: list[dict[str, Any]] = []
            for start, end in intervals:
                if merged and start < merged[-1][1] and (start, end) != (merged[-1][0], merged[-1][1]):
                    collision_details.append(
                        {
                            "start": str(start),
                            "end": str(end),
                            "previous_end": str(merged[-1][1]),
                            "event_ids": by_span[(start, end)],
                        }
                    )
                if not merged or start > merged[-1][1]:
                    merged.append([start, end])
                else:
                    merged[-1][1] = max(merged[-1][1], end)
            for details in collision_details:
                report.add_error(
                    ValidationIssue(
                        "E08",
                        f"{location} contains overlapping non-chord events",
                        "duration",
                        details=details,
                    )
                )
            gaps: list[tuple[Fraction, Fraction]] = []
            cursor = Fraction(0)
            for start, end in merged:
                if start > cursor:
                    gaps.append((cursor, start))
                cursor = max(cursor, end)
            actual = cursor
            if actual < expected:
                gaps.append((actual, expected))
            totals[location] = str(actual)
            coverage[location] = {
                "covered": str(sum((end - start for start, end in merged), Fraction(0))),
                "gaps": [{"start": str(start), "end": str(end)} for start, end in gaps],
                "collisions": collision_details,
            }
            if actual > expected:
                report.add_error(
                    ValidationIssue(
                        "E07",
                        f"{location} duration {actual} exceeds meter capacity {expected}",
                        "duration",
                        details={"actual": str(actual), "expected": str(expected)},
                    )
                )
            elif gaps and not (pickup and measure_index == 0):
                report.add_warning(
                    ValidationIssue(
                        "E07",
                        f"{location} contains uncovered time; exporter may add rests",
                        "duration",
                        details={
                            "actual": str(actual),
                            "expected": str(expected),
                            "gaps": coverage[location]["gaps"],
                        },
                    )
                )
    report.checks.update(
        {
            "expected_quarters": str(expected),
            "voice_end_positions": totals,
            "voice_coverage": coverage,
            "pickup_first_measure_allowed": pickup,
        }
    )
    return report

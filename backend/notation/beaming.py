"""Meter-aware MusicXML beam assignment for ScoreDocument events."""

from __future__ import annotations

import copy
from fractions import Fraction
from typing import Any

from backend.notation.duration_math import duration_to_fraction


HOST_AUTHORED_SCORE_SOURCES = {"imported", "sera_edit_roundtrip"}


def materialize_beams_for_score_document(score_document: dict[str, Any]) -> dict[str, Any]:
    """Preserve host-authored beams, while deriving beams for Sera-owned scores.

    MusicXML imported from a notation host may contain intentional cross-beat
    or cross-staff beaming that the local meter-only beam engine cannot
    reconstruct.  Such scores keep both explicit beam values and intentional
    beam absence.  Sera-generated/edited documents continue to receive the
    deterministic automatic beaming used by the exporter.
    """

    score = copy.deepcopy(score_document or {})
    source = str((score.get("metadata") or {}).get("source", "")).strip().lower()
    if source in HOST_AUTHORED_SCORE_SOURCES or source.endswith("_bridge"):
        return score
    return assign_beams_to_score_document(score)


def assign_beams_to_score_document(score_document: dict[str, Any]) -> dict[str, Any]:
    score = copy.deepcopy(score_document or {})
    meter = str(score.get("global", {}).get("meter", "4/4"))
    for measure in score.get("measures", []):
        measure["events"] = assign_beams_to_measure(list(measure.get("events") or []), meter)
    score.setdefault("metadata", {})["beaming_assigned"] = True
    return score


def assign_beams_to_measure(events: list[dict[str, Any]], meter: str) -> list[dict[str, Any]]:
    annotated = [dict(event) for event in events]
    for event in annotated:
        event.pop("beam", None)
        event.pop("beam_group", None)
    for group in compute_beam_groups(annotated, meter):
        group_events = group["events"]
        if len(group_events) < 2:
            continue
        for index, event in enumerate(group_events):
            event["beam_group"] = group["beam_group"]
            event["beam"] = {
                "number": 1,
                "value": "begin" if index == 0 else "end" if index == len(group_events) - 1 else "continue",
            }
    return annotated


def compute_beam_groups(events: list[dict[str, Any]], meter: str) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    group_span = Fraction(3, 2) if meter == "6/8" else Fraction(1, 1)
    by_lane: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for event in events:
        staff = str(event.get("staff", "right_hand"))
        voice = int(event.get("voice", 1) or 1)
        by_lane.setdefault((staff, voice), []).append(event)
    for (staff, voice), lane_events in by_lane.items():
        current: list[dict[str, Any]] = []
        current_key: int | None = None
        expected_next: Fraction | None = None
        for event in sorted(lane_events, key=lambda item: (Fraction(str(item.get("offset", 0))), str(item.get("event_id", "")))):
            start = Fraction(str(event.get("offset", 0)))
            duration = duration_to_fraction(str(event.get("duration", "quarter")))
            key = int(start / group_span)
            if not _beamable(event, duration) or key != current_key or (expected_next is not None and start != expected_next):
                _append_group(groups, current, staff, voice, current_key)
                current = []
                current_key = key
            if _beamable(event, duration):
                current.append(event)
                expected_next = start + duration
            else:
                expected_next = None
        _append_group(groups, current, staff, voice, current_key)
    return groups


def _append_group(groups: list[dict[str, Any]], current: list[dict[str, Any]], staff: str, voice: int, key: int | None) -> None:
    if len(current) < 2 or key is None:
        return
    groups.append({"beam_group": f"{staff}:{voice}:{key}", "staff": staff, "voice": voice, "events": list(current)})


def _beamable(event: dict[str, Any], duration: Fraction) -> bool:
    if event.get("type") == "rest":
        return False
    if duration > Fraction(1, 2):
        return False
    return str(event.get("duration", "")).replace("-", "_") in {"eighth", "sixteenth"}

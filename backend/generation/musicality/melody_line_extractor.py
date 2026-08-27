"""Extract melody-line views from canonical ScoreDocument data."""

from __future__ import annotations

import copy
from typing import Any

from evaluation.analysis.music_statistics import parse_pitch_name


def extract_melody_lines(score_document: dict[str, Any], options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return staff/voice melody candidates without merging accompaniment."""

    options = options or {}
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    excluded_lines: list[dict[str, Any]] = []
    warnings: list[str] = []
    for measure in score_document.get("measures", []) or []:
        measure_number = int(measure.get("number", 1) or 1)
        for event in measure.get("events", []) or []:
            if event.get("type") == "rest":
                continue
            pitch = str(event.get("pitch") or "")
            midi = parse_pitch_name(pitch)
            if midi is None:
                continue
            staff = _staff_label(event.get("staff"))
            voice = int(event.get("voice", 1) or 1)
            grouped.setdefault((staff, voice), []).append(
                {
                    **copy.deepcopy(event),
                    "measure_number": measure_number,
                    "measure_id": str(measure.get("measure_id", f"m{measure_number}")),
                    "midi": midi,
                    "role": "primary_melody" if staff == "right_hand" and voice == 1 else "candidate",
                }
            )

    melody_lines: list[dict[str, Any]] = []
    for (staff, voice), events in grouped.items():
        ordered = sorted(events, key=lambda item: (int(item.get("measure_number", 1)), float(item.get("offset", 0.0))))
        line = {
            "line_id": f"{staff}_voice_{voice}",
            "staff": staff,
            "voice": voice,
            "events": ordered,
            "pitches": [int(item["midi"]) for item in ordered],
            "measure_range": _measure_range(ordered),
            "phrase_ranges": _phrase_ranges(ordered, options),
            "role": "primary_melody" if staff == "right_hand" and voice == 1 else "accompaniment" if staff == "left_hand" else "secondary",
        }
        if staff == "left_hand":
            excluded_lines.append({"staff": staff, "voice": voice, "reason": "accompaniment", "note_count": len(ordered)})
        melody_lines.append(line)

    primary = _select_primary_line(melody_lines)
    if not primary and melody_lines:
        primary = max(melody_lines, key=lambda line: len(line.get("events", [])))
        warnings.append("Primary melody fallback used because right_hand voice 1 was unavailable.")
    if not primary:
        primary = {"staff": "right_hand", "voice": 1, "events": [], "pitches": [], "measure_range": [], "phrase_ranges": []}
        warnings.append("No melody notes found.")
    return {
        "primary_melody": primary,
        "melody_lines": melody_lines,
        "excluded_lines": excluded_lines,
        "warnings": warnings,
    }


def extract_primary_melody_line(score_document: dict[str, Any], options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return only the selected primary melody line."""

    return extract_melody_lines(score_document, options).get("primary_melody", {})


def _staff_label(value: Any) -> str:
    text = str(value or "").strip()
    if text in {"2", "left", "left_hand", "bass"}:
        return "left_hand"
    if text in {"", "1", "right", "right_hand", "treble"}:
        return "right_hand"
    return text


def _select_primary_line(lines: list[dict[str, Any]]) -> dict[str, Any] | None:
    for line in lines:
        if line.get("staff") == "right_hand" and int(line.get("voice", 1) or 1) == 1:
            return line
    right_lines = [line for line in lines if line.get("staff") == "right_hand"]
    return max(right_lines, key=lambda line: len(line.get("events", [])), default=None)


def _measure_range(events: list[dict[str, Any]]) -> list[int]:
    if not events:
        return []
    numbers = [int(event.get("measure_number", 1) or 1) for event in events]
    return [min(numbers), max(numbers)]


def _phrase_ranges(events: list[dict[str, Any]], options: dict[str, Any]) -> list[list[int]]:
    if not events:
        return []
    phrase_length = int(options.get("phrase_length", 4) or 4)
    start, end = _measure_range(events)
    return [[measure, min(end, measure + phrase_length - 1)] for measure in range(start, end + 1, phrase_length)]

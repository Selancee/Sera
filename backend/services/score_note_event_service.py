"""Detailed note-event views derived from the canonical ScoreDocument."""

from __future__ import annotations

from typing import Any

from backend.services.score_document_service import duration_to_quarters, normalize_score_document
from evaluation.analysis.music_statistics import parse_pitch_name


def score_document_to_playback_note_events(score_document: dict[str, Any]) -> list[dict[str, Any]]:
    """Return frontend-friendly note events with measure, staff, and timing."""

    score = normalize_score_document(score_document)
    tempo = int(score.get("global", {}).get("tempo", 90) or 90)
    beats, beat_type = _parse_meter(str(score.get("global", {}).get("meter", "4/4")))
    measure_quarters = beats * (4 / beat_type)
    seconds_per_quarter = 60.0 / max(1, tempo)
    note_events: list[dict[str, Any]] = []
    for measure in score.get("measures", []):
        measure_number = int(measure.get("number", 1) or 1)
        measure_start_quarters = (measure_number - 1) * measure_quarters
        for event in measure.get("events", []):
            if event.get("type") == "rest":
                continue
            pitch = str(event.get("pitch", ""))
            midi = parse_pitch_name(pitch)
            if midi is None:
                continue
            duration_quarters = duration_to_quarters(str(event.get("duration", "quarter")))
            offset = float(event.get("offset", 0.0) or 0.0)
            start_quarters = measure_start_quarters + offset
            note_events.append(
                {
                    "event_id": str(event.get("event_id", "")),
                    "measure_id": str(measure.get("measure_id", f"m{measure_number}")),
                    "measure_number": measure_number,
                    "staff": str(event.get("staff", "right_hand")),
                    "voice": int(event.get("voice", 1) or 1),
                    "pitch": pitch,
                    "midi": midi,
                    "duration": str(event.get("duration", "quarter")),
                    "duration_seconds": round(duration_quarters * seconds_per_quarter, 4),
                    "offset_beats": offset,
                    "start_seconds": round(start_quarters * seconds_per_quarter, 4),
                    "dynamic": str(event.get("dynamic", "mf")),
                    "diagnostic_stream": "playback_event_stream",
                    "melody_diagnostic_eligible": False,
                }
            )
    return sorted(note_events, key=lambda item: (item["start_seconds"], item["staff"], item["voice"], item["midi"]))


def _parse_meter(meter: str) -> tuple[int, int]:
    try:
        beats, beat_type = meter.split("/", 1)
        return int(beats), int(beat_type)
    except (AttributeError, ValueError):
        return 4, 4

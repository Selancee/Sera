"""Consistency checks for V0.92 authoritative score generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evaluation.analysis.music_statistics import parse_musicxml_notes


class ScoreConsistencyService:
    """Compare MusicXML, ScoreDocument, and MIDI event views of a score."""

    def build_report(
        self,
        musicxml: str = "",
        score_document: dict[str, Any] | None = None,
        midi_note_events: list[dict[str, Any]] | None = None,
        midi_path: str | Path | None = None,
    ) -> dict[str, Any]:
        score_document = score_document or {}
        midi_note_events = midi_note_events or []
        mismatches: list[dict[str, Any]] = []
        warnings: list[str] = []
        errors: list[str] = []

        musicxml_notes = []
        if musicxml:
            try:
                musicxml_notes = parse_musicxml_notes(musicxml)
            except Exception as exc:  # noqa: BLE001 - report should be robust.
                errors.append(f"MusicXML parse failed for consistency check: {exc}")
        else:
            errors.append("Missing MusicXML.")

        measures = score_document.get("measures") if isinstance(score_document, dict) else None
        if not measures:
            errors.append("Missing score_document.")
            measures = []

        musicxml_event_count = len(musicxml_notes)
        score_document_event_count = sum(len(measure.get("events", [])) for measure in measures)
        note_event_count = sum(1 for measure in measures for event in measure.get("events", []) if event.get("type") != "rest")
        midi_event_count = len(midi_note_events)
        measure_count_musicxml = len({int(getattr(note, "measure", 0) or 0) for note in musicxml_notes}) if musicxml_notes else musicxml.count("<measure")
        measure_count_score_document = len(measures)

        self._append_count_mismatch(
            mismatches,
            "musicxml_vs_score_document_events",
            musicxml_event_count,
            score_document_event_count,
            tolerance=max(2, int(score_document_event_count * 0.08)),
        )
        self._append_count_mismatch(
            mismatches,
            "score_document_notes_vs_midi_events",
            note_event_count,
            midi_event_count,
            tolerance=max(1, int(note_event_count * 0.05)),
        )
        self._append_count_mismatch(
            mismatches,
            "musicxml_vs_score_document_measures",
            measure_count_musicxml,
            measure_count_score_document,
            tolerance=0,
        )

        staffs = {str(event.get("staff", "right_hand")) for measure in measures for event in measure.get("events", [])}
        voices = {int(event.get("voice", 1) or 1) for measure in measures for event in measure.get("events", [])}
        if "left_hand" not in staffs:
            warnings.append("No left-hand events found in ScoreDocument.")
        if not midi_path or not Path(midi_path).exists():
            warnings.append("Generated MIDI file is missing.")
        empty_measures = [measure.get("number", index + 1) for index, measure in enumerate(measures) if not measure.get("events")]
        if empty_measures:
            warnings.append(f"Empty ScoreDocument measures: {empty_measures[:12]}")

        report = {
            "musicxml_event_count": musicxml_event_count,
            "score_document_event_count": score_document_event_count,
            "midi_event_count": midi_event_count,
            "note_event_count": note_event_count,
            "measure_count_musicxml": measure_count_musicxml,
            "measure_count_score_document": measure_count_score_document,
            "staff_count_score_document": len(staffs),
            "voice_count_score_document": len(voices),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
            "valid": not errors and not mismatches,
            "warnings": warnings,
            "errors": errors,
        }
        return report

    @staticmethod
    def _append_count_mismatch(
        mismatches: list[dict[str, Any]],
        check: str,
        expected: int,
        actual: int,
        tolerance: int,
    ) -> None:
        if abs(expected - actual) <= tolerance:
            return
        mismatches.append(
            {
                "check": check,
                "expected": expected,
                "actual": actual,
                "tolerance": tolerance,
            }
        )

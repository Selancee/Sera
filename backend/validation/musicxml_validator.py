"""MusicXML validity, completeness, export, and pitch-range checks."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from backend.models.schemas import CompositionPlan, ValidationResult


STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
INSTRUMENT_RANGES = {
    "piano": (21, 108),
    "violin": (55, 103),
    "cello": (36, 84),
    "flute": (60, 96),
    "clarinet": (50, 94),
    "guitar": (40, 88),
    "voice": (48, 84),
    "synthesizer": (36, 96),
}


class MusicXMLValidator:
    """Validate generated MusicXML with XML checks and optional music21 parsing."""

    def validate_text(
        self,
        musicxml: str,
        plan: CompositionPlan | None = None,
        min_midi: int | None = None,
        max_midi: int | None = None,
        midi_path: str | Path | None = None,
        pdf_path: str | Path | None = None,
    ) -> ValidationResult:
        """Validate MusicXML parseability, measure integrity, range, and exports."""

        issues: list[str] = []
        warnings: list[str] = []
        low, high = self._range_for_plan(plan, min_midi, max_midi)
        metrics: dict[str, Any] = {
            "valid_musicxml": False,
            "musicxml_parseable": False,
            "music21_parseable": False,
            "musicxml_exportable": False,
            "measure_count": 0,
            "expected_measure_count": plan.intent.bars if plan else None,
            "measure_count_match": True if plan is None else False,
            "bar_completeness": 0.0,
            "bar_completeness_score": 0.0,
            "pitch_range_valid": True,
            "pitch_count": 0,
            "empty_measure_count": 0,
            "midi_export_success": self._path_success(midi_path) if midi_path else True,
            "pdf_export_success": self._path_success(pdf_path) if pdf_path else True,
        }

        try:
            root = ET.fromstring(musicxml)
            metrics["musicxml_parseable"] = root.tag.endswith("score-partwise")
        except ET.ParseError as exc:
            return ValidationResult(
                valid=False,
                issues=[f"MusicXML parse error: {exc}"],
                warnings=warnings,
                metrics=metrics,
            )

        metrics["music21_parseable"] = self._music21_parseable(musicxml, warnings, issues)
        metrics["musicxml_exportable"] = bool(metrics["musicxml_parseable"] and metrics["music21_parseable"])
        metrics["valid_musicxml"] = metrics["musicxml_exportable"]

        divisions = 1
        beats = 4
        beat_type = 4
        complete = 0
        measures = root.findall(".//measure")
        metrics["measure_count"] = len(measures)
        if plan is not None:
            metrics["measure_count_match"] = len(measures) == plan.intent.bars
            if not metrics["measure_count_match"]:
                issues.append(f"Measure count {len(measures)} != plan length {plan.intent.bars}")

        for measure in measures:
            attr = measure.find("attributes")
            if attr is not None:
                divisions = self._int_text(attr.find("divisions"), divisions)
                time = attr.find("time")
                if time is not None:
                    beats = self._int_text(time.find("beats"), beats)
                    beat_type = self._int_text(time.find("beat-type"), beat_type)

            expected = int(beats * divisions * (4 / beat_type))
            voice_totals: dict[tuple[str, str], int] = {}
            pitched_in_measure = 0
            note_count = 0
            for note in measure.findall("note"):
                note_count += 1
                duration = self._int_text(note.find("duration"), 0)
                staff = note.findtext("staff") or "1"
                voice = note.findtext("voice") or "1"
                if note.find("chord") is None:
                    voice_totals[(staff, voice)] = voice_totals.get((staff, voice), 0) + duration
                pitch = note.find("pitch")
                if pitch is not None:
                    pitched_in_measure += 1
                    midi_number = self._pitch_to_midi(pitch)
                    metrics["pitch_count"] += 1
                    if midi_number < low or midi_number > high:
                        metrics["pitch_range_valid"] = False
                        issues.append(
                            f"Measure {measure.get('number', '?')}: pitch {midi_number} outside {low}-{high}"
                        )
            if note_count == 0 or pitched_in_measure == 0:
                metrics["empty_measure_count"] += 1
                issues.append(f"Measure {measure.get('number', '?')}: empty measure")

            if voice_totals and all(total == expected for total in voice_totals.values()):
                complete += 1
            else:
                details = ", ".join(f"staff {staff}/voice {voice}={total}" for (staff, voice), total in voice_totals.items())
                issues.append(
                    f"Measure {measure.get('number', '?')}: incomplete duration ({details or 'none'}), expected {expected}"
                )

        metrics["bar_completeness"] = complete / len(measures) if measures else 0.0
        metrics["bar_completeness_score"] = metrics["bar_completeness"]
        if not measures:
            issues.append("No measures found")
        if metrics["pitch_count"] == 0:
            issues.append("No pitched notes found")
        if midi_path and not metrics["midi_export_success"]:
            issues.append(f"MIDI export missing or empty: {midi_path}")
        if pdf_path and not metrics["pdf_export_success"]:
            issues.append(f"PDF export missing or empty: {pdf_path}")

        return ValidationResult(
            valid=not issues and bool(metrics["valid_musicxml"]),
            issues=issues,
            warnings=warnings,
            metrics=metrics,
        )

    def validate_file(self, path: str | Path, plan: CompositionPlan | None = None) -> ValidationResult:
        """Validate a MusicXML file path."""

        return self.validate_text(Path(path).read_text(encoding="utf-8"), plan=plan)

    @staticmethod
    def _range_for_plan(
        plan: CompositionPlan | None,
        min_midi: int | None,
        max_midi: int | None,
    ) -> tuple[int, int]:
        if min_midi is not None and max_midi is not None:
            return min_midi, max_midi
        if plan is None:
            return 21, 108
        for instrument in plan.intent.instruments:
            for key, midi_range in INSTRUMENT_RANGES.items():
                if key in instrument.lower():
                    return midi_range
        return 36, 96

    @staticmethod
    def _music21_parseable(musicxml: str, warnings: list[str], issues: list[str]) -> bool:
        try:
            from music21 import converter  # type: ignore
        except ImportError:
            # TODO: surface optional dependency state in the frontend validator panel.
            warnings.append("music21 is not installed; XML-only validation used")
            return True
        try:
            converter.parseData(musicxml)
            return True
        except Exception as exc:  # noqa: BLE001 - music21 raises varied parser exceptions.
            issues.append(f"music21 parse error: {exc}")
            return False

    @staticmethod
    def _path_success(path: str | Path | None) -> bool:
        if path is None:
            return False
        target = Path(path)
        return target.exists() and target.stat().st_size > 0

    @staticmethod
    def _int_text(node: ET.Element | None, fallback: int) -> int:
        if node is None or node.text is None:
            return fallback
        try:
            return int(node.text.strip())
        except ValueError:
            return fallback

    @staticmethod
    def _pitch_to_midi(pitch_node: ET.Element) -> int:
        step = (pitch_node.findtext("step") or "C").strip()
        alter = int(pitch_node.findtext("alter") or 0)
        octave = int(pitch_node.findtext("octave") or 4)
        return (octave + 1) * 12 + STEP_TO_SEMITONE.get(step, 0) + alter

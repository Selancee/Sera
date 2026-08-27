import itertools
import re
from typing import Any

from backend.pipeline import SeraPipeline


PITCH_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
STEP_INDEX = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
DURATION_QUARTERS = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "sixteenth": 0.25,
    "dotted_quarter": 1.5,
    "dotted_half": 3.0,
}


def test_final_score_avoids_augmented_unison_octave_spelling_collisions(tmp_path) -> None:
    pipeline = SeraPipeline(tmp_path)
    cases = [
        ("romantic flowing nocturne piano, 8 measures in A minor", "vertical-debug-1"),
        ("pop piano song, 8 measures in E major", "vertical-debug-2"),
        ("cyberpunk piano passage, dark futuristic ostinato, 8 measures in A minor", "vertical-debug-4"),
    ]

    for prompt, seed in cases:
        result = pipeline.generate(
            prompt,
            generator_mode="rule_based",
            musicality_controls={"variation_seed": seed, "candidate_count": 4},
        )

        assert _augmented_unison_octave_collisions(result["score_document"]) == []


def test_key_spelling_survives_musicxml_to_score_document_roundtrip(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "pop piano song, 8 measures in E major",
        generator_mode="rule_based",
        musicality_controls={"variation_seed": "vertical-debug-2", "candidate_count": 4},
    )

    pitches = {
        event.get("pitch")
        for measure in result["score_document"]["measures"]
        for event in measure.get("events", [])
        if event.get("type") != "rest"
    }
    assert "G#3" in pitches or "G#4" in pitches
    assert "D#4" in pitches or "D#5" in pitches
    assert "Ab3" not in pitches
    assert "Eb4" not in pitches


def test_minor_dominant_measures_align_melody_to_raised_leading_tone(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "classical piano theme, 8 measures in A minor",
        generator_mode="rule_based",
        musicality_controls={"variation_seed": "vertical-debug-5", "candidate_count": 4},
    )
    chords = result["generation_metadata"]["harmony_plan"]["chords"]
    score_document = result["score_document"]

    for measure in score_document["measures"]:
        chord = str(chords[int(measure["number"]) - 1])
        if chord not in {"V", "V7"} and not chord.startswith("V/"):
            continue
        right_pitches = [
            event.get("pitch")
            for event in measure.get("events", [])
            if event.get("staff") != "left_hand" and event.get("type") != "rest"
        ]
        assert "G4" not in right_pitches
        assert "G5" not in right_pitches


def test_minor_tonic_and_subdominant_left_hand_do_not_become_major(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "romantic flowing nocturne piano, 8 measures in A minor",
        generator_mode="rule_based",
        musicality_controls={"variation_seed": "vertical-debug-5", "candidate_count": 4},
    )
    chords = result["generation_metadata"]["harmony_plan"]["chords"]
    score_document = result["score_document"]

    for measure in score_document["measures"]:
        chord = str(chords[int(measure["number"]) - 1])
        left_pitches = {
            event.get("pitch")
            for event in measure.get("events", [])
            if event.get("staff") == "left_hand" and event.get("type") != "rest"
        }
        if chord in {"i", "I"}:
            assert not any(str(pitch).startswith("C#") for pitch in left_pitches)
            assert any(str(pitch).startswith("C") for pitch in left_pitches)
        if chord in {"iv", "IV"}:
            assert not any(str(pitch).startswith("F#") for pitch in left_pitches)
            assert any(str(pitch).startswith("F") for pitch in left_pitches)


def test_measure_does_not_mix_same_letter_natural_and_accidental_across_staves(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "romantic flowing nocturne piano, 8 measures in A minor",
        generator_mode="rule_based",
        musicality_controls={"variation_seed": "measure-conflict-0", "candidate_count": 4},
    )

    assert _measure_accidental_conflicts(result["score_document"]) == []


def test_final_score_removes_redundant_same_pitch_events(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "romantic flowing nocturne piano, 8 measures in A minor",
        generator_mode="rule_based",
        musicality_controls={"variation_seed": "measure-conflict-0", "candidate_count": 4},
    )

    assert _duplicate_note_events(result["score_document"]) == []


def test_measure_accidental_repair_preserves_same_staff_chromatic_motion() -> None:
    measure = {
        "number": 1,
        "events": [
            {"type": "note", "event_id": "n1", "pitch": "C4", "staff": "right_hand", "voice": 1, "offset": 0.0, "duration": "eighth"},
            {"type": "note", "event_id": "n2", "pitch": "C#4", "staff": "right_hand", "voice": 1, "offset": 0.5, "duration": "eighth"},
        ],
    }

    repairs = SeraPipeline._repair_final_measure_accidental_consistency(measure, "C major", "major", 1)

    assert repairs == []
    assert [event["pitch"] for event in measure["events"]] == ["C4", "C#4"]


def _augmented_unison_octave_collisions(score_document: dict[str, Any]) -> list[dict[str, Any]]:
    events = _active_events(score_document)
    collisions: list[dict[str, Any]] = []
    for measure_number in sorted({event["measure"] for event in events}):
        measure_events = [event for event in events if event["measure"] == measure_number]
        times = sorted(
            {round(event["start"], 4) for event in measure_events}
            | {round(event["end"], 4) for event in measure_events}
        )
        for time in times:
            sounding = [event for event in measure_events if event["start"] <= time < event["end"]]
            for left, right in itertools.combinations(sounding, 2):
                if left["staff"] == right["staff"] and left["voice"] == right["voice"]:
                    continue
                if _is_augmented_unison_or_octave(left["pitch"], right["pitch"]):
                    collisions.append(
                        {
                            "measure": measure_number,
                            "time": time,
                            "pitches": [left["pitch"], right["pitch"]],
                        }
                    )
    return collisions


def _measure_accidental_conflicts(score_document: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for measure in score_document.get("measures", []):
        by_step: dict[str, list[str]] = {}
        for event in measure.get("events", []):
            if event.get("type") == "rest":
                continue
            match = re.match(r"^([A-G])([#b]*)(-?\d+)$", str(event.get("pitch", "")))
            if not match:
                continue
            step, accidental, _octave = match.groups()
            by_step.setdefault(step, []).append(accidental or "natural")
        for step, accidentals in by_step.items():
            if len(set(accidentals)) > 1:
                conflicts.append({"measure": int(measure.get("number", 1) or 1), "step": step, "accidentals": sorted(set(accidentals))})
    return conflicts


def _duplicate_note_events(score_document: dict[str, Any]) -> list[dict[str, Any]]:
    duplicates: list[dict[str, Any]] = []
    for measure in score_document.get("measures", []):
        seen: set[tuple[str, int, float, str, str]] = set()
        for event in measure.get("events", []):
            if event.get("type") == "rest":
                continue
            key = (
                str(event.get("staff", "right_hand")),
                int(event.get("voice", 1) or 1),
                round(float(event.get("offset", 0.0) or 0.0), 4),
                str(event.get("duration", "quarter")),
                str(event.get("pitch", "")),
            )
            if key in seen:
                duplicates.append({"measure": int(measure.get("number", 1) or 1), "key": key})
            seen.add(key)
    return duplicates


def _active_events(score_document: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for measure in score_document.get("measures", []):
        measure_number = int(measure.get("number", 1) or 1)
        for event in measure.get("events", []):
            if event.get("type") == "rest":
                continue
            start = float(event.get("offset", 0.0) or 0.0)
            duration = DURATION_QUARTERS.get(str(event.get("duration", "quarter")), 1.0)
            events.append(
                {
                    "measure": measure_number,
                    "staff": str(event.get("staff", "right_hand")),
                    "voice": int(event.get("voice", 1) or 1),
                    "start": start,
                    "end": start + duration,
                    "pitch": str(event.get("pitch", "")),
                }
            )
    return events


def _is_augmented_unison_or_octave(first: str, second: str) -> bool:
    left = _parse_pitch(first)
    right = _parse_pitch(second)
    if not left or not right:
        return False
    lower, upper = (left, right) if left["midi"] <= right["midi"] else (right, left)
    semitones = (upper["midi"] - lower["midi"]) % 12
    letter_span = (upper["letter"] - lower["letter"]) % 7
    return letter_span == 0 and semitones == 1


def _parse_pitch(pitch: str) -> dict[str, int] | None:
    match = re.match(r"^([A-G])([#b]*)(-?\d+)$", pitch)
    if not match:
        return None
    step, accidental, octave_text = match.groups()
    octave = int(octave_text)
    pc = (PITCH_PC[step] + accidental.count("#") - accidental.count("b")) % 12
    return {
        "midi": (octave + 1) * 12 + pc,
        "letter": STEP_INDEX[step] + 7 * octave,
    }

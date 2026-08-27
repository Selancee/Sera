from __future__ import annotations

import copy

from sera_edit.validation.duration_validator import duration_fraction, validate_measure_durations
from sera_edit.validation.notation_relation_validator import validate_notation_relations


def test_triplet_duration_is_exact_fraction() -> None:
    assert str(duration_fraction("triplet_eighth")) == "1/3"


def test_duration_validator_accepts_independent_complete_voices(two_staff_score: dict) -> None:
    score = copy.deepcopy(two_staff_score)
    score["measures"][0]["events"].append(
        {
            "event_id": "m1_voice2",
            "type": "note",
            "pitch": "C3",
            "duration": "whole",
            "offset": 0,
            "voice": 2,
            "staff": "right_hand",
            "tie": None,
            "slur": None,
            "dynamic": "mf",
            "articulations": [],
        }
    )
    report = validate_measure_durations(score)
    assert report.status == "valid"
    assert report.checks["voice_end_positions"]["m1:right_hand:v2"] == "4"


def test_duration_validator_rejects_voice_collision(two_staff_score: dict) -> None:
    score = copy.deepcopy(two_staff_score)
    score["measures"][0]["events"].append(
        {
            "event_id": "collision",
            "type": "note",
            "pitch": "G4",
            "duration": "half",
            "offset": 0.5,
            "voice": 1,
            "staff": "right_hand",
        }
    )
    report = validate_measure_durations(score)
    assert "E08" in {issue.code for issue in report.errors}


def test_notation_validator_accepts_well_formed_chord(two_staff_score: dict) -> None:
    score = copy.deepcopy(two_staff_score)
    first = score["measures"][0]["events"][0]
    first["chord_group_id"] = "m1_chord"
    first["is_chord_tone"] = False
    chord_tone = copy.deepcopy(first)
    chord_tone["event_id"] = "m1_chord_e"
    chord_tone["pitch"] = "E4"
    chord_tone["is_chord_tone"] = True
    score["measures"][0]["events"].append(chord_tone)
    assert validate_notation_relations(score).status == "valid"


def test_notation_validator_rejects_unequal_chord_duration(two_staff_score: dict) -> None:
    score = copy.deepcopy(two_staff_score)
    first = score["measures"][0]["events"][0]
    first["chord_group_id"] = "bad_chord"
    first["is_chord_tone"] = False
    chord_tone = copy.deepcopy(first)
    chord_tone["event_id"] = "bad_chord_e"
    chord_tone["pitch"] = "E4"
    chord_tone["duration"] = "half"
    chord_tone["is_chord_tone"] = True
    score["measures"][0]["events"].append(chord_tone)
    report = validate_notation_relations(score)
    assert "E08" in {issue.code for issue in report.errors}


def test_notation_validator_rejects_tie_on_rest(two_staff_score: dict) -> None:
    score = copy.deepcopy(two_staff_score)
    event = score["measures"][0]["events"][0]
    event.update({"type": "rest", "pitch": "", "tie": "start"})
    report = validate_notation_relations(score)
    assert "E09" in {issue.code for issue in report.errors}

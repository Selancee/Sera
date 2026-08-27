from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.benchmark_io import load_task, resolve_task_path
from scripts.validate_benchmark import evaluate_constraints


def test_task_resolver_falls_back_to_incremental_batch(tmp_path: Path) -> None:
    path = tmp_path / "tasks" / "batch1" / "pitch_001.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"task_id": "pitch_001"}), encoding="utf-8")
    assert resolve_task_path(tmp_path, "pitch_001", "core") == path
    assert load_task(tmp_path, "pitch_001", "core")["task_id"] == "pitch_001"


def test_task_resolver_rejects_ambiguous_ids(tmp_path: Path) -> None:
    for batch in ("batch1", "batch2"):
        path = tmp_path / "tasks" / batch / "duplicate.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_task_path(tmp_path, "duplicate")


def test_extended_constraints_are_deterministic(two_staff_score: dict) -> None:
    after = json.loads(json.dumps(two_staff_score))
    event = after["measures"][0]["events"][0]
    event.update({"pitch": "D4", "articulations": ["staccato"], "voice": 2, "slur": "start"})
    after["global"]["meter"] = "2/2"
    valid, errors = evaluate_constraints(
        two_staff_score,
        after,
        [
            {"type": "pitch_equals", "event_id": "m1_rh_1", "value": "D4"},
            {"type": "articulation_equals", "event_id": "m1_rh_1", "value": ["staccato"]},
            {"type": "voice_equals", "event_id": "m1_rh_1", "value": 2},
            {"type": "slur_equals", "event_id": "m1_rh_1", "value": "start"},
            {"type": "meter_equals", "value": "2/2"},
        ],
    )
    assert valid is True
    assert errors == []


def test_insert_and_chord_constraints_accept_equivalent_generator_owned_ids(two_staff_score: dict) -> None:
    inserted = json.loads(json.dumps(two_staff_score))
    inserted["measures"][0]["events"].append(
        {
            "event_id": "runtime_replacement",
            "type": "note",
            "pitch": "F#4",
            "duration": "quarter",
            "offset": 4,
            "voice": 1,
            "staff": "right_hand",
        }
    )
    valid, errors = evaluate_constraints(
        two_staff_score,
        inserted,
        [{"type": "event_inserted", "event_id": "gold_replacement", "pitch": "F#4"}],
    )
    assert valid is True
    assert errors == []

    chord = json.loads(json.dumps(two_staff_score))
    for index, pitch in enumerate(("C4", "E4", "G4"), start=1):
        chord["measures"][0]["events"].append(
            {
                "event_id": f"runtime_chord_{index}",
                "type": "note",
                "pitch": pitch,
                "duration": "quarter",
                "offset": 4,
                "voice": 1,
                "staff": "right_hand",
            }
        )
    valid, errors = evaluate_constraints(
        two_staff_score,
        chord,
        [
            {
                "type": "chord_pitches",
                "event_ids": ["gold_chord_1", "gold_chord_2", "gold_chord_3"],
                "value": ["C4", "E4", "G4"],
            }
        ],
    )
    assert valid is True
    assert errors == []

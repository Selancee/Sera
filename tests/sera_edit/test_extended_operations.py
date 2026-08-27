from __future__ import annotations

from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.execution.transaction import PatchTransaction


def _patch(score: dict, operation: dict, target_scope: dict | None = None) -> dict:
    return {
        "schema_version": "1.0.0",
        "patch_id": f"patch_{operation['operation_id']}",
        "source_score_id": score["score_id"],
        "source_fingerprint": score_fingerprint(score),
        "instruction": "Apply an extended operation fixture.",
        "target_scope": target_scope or {"measures": [1], "staffs": [1]},
        "protected_scope": {"staffs": [2]},
        "preconditions": [],
        "operations": [operation],
        "expected_effects": [],
        "provenance": {"provider": "test", "model": "deterministic", "seed": 42},
    }


def test_replace_chord_creates_one_primary_and_roundtrips(two_staff_score: dict) -> None:
    operation = {
        "operation_id": "replace_c_major",
        "type": "replace_chord",
        "selector": {"event_ids": ["m1_rh_1"]},
        "arguments": {"pitches": ["C4", "E4", "G4"]},
        "preconditions": [],
        "expected_change_count": 4,
    }
    result = PatchTransaction().execute(two_staff_score, _patch(two_staff_score, operation))
    assert result.committed is True
    chord = [
        event
        for event in result.score_document["measures"][0]["events"]
        if event.get("chord_group_id") == "replace_c_major"
    ]
    assert [event["is_chord_tone"] for event in chord] == [False, True, True]
    assert result.report.checks["roundtrip_fidelity"]["status"] == "valid"


def test_insert_note_preserves_grace_and_chord_metadata(two_staff_score: dict) -> None:
    operation = {
        "operation_id": "insert_grace",
        "type": "insert_note",
        "selector": {"measure": 1},
        "arguments": {
            "event_id": "m1_grace",
            "pitch": "B3",
            "duration": "eighth",
            "offset": 0,
            "voice": 1,
            "staff": "right_hand",
            "grace": True,
            "articulations": ["accent"],
        },
        "preconditions": [],
        "expected_change_count": 1,
    }
    result = PatchTransaction().execute(two_staff_score, _patch(two_staff_score, operation))
    assert result.committed is True
    inserted = next(
        event
        for event in result.score_document["measures"][0]["events"]
        if event["event_id"] == "m1_grace"
    )
    assert inserted["grace"] is True
    assert inserted["articulations"] == ["accent"]

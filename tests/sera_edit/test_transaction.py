from __future__ import annotations

import copy

from backend.services.score_document_service import new_score_document, normalize_score_document
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.execution.transaction import PatchTransaction
from sera_edit.execution.undo_manager import UndoManager


def make_patch(score: dict, *, event_ids: list[str] | None = None, op_type: str = "transpose", arguments: dict | None = None) -> dict:
    event_ids = event_ids or [f"m1_rh_{index}" for index in range(1, 5)]
    return {
        "schema_version": "1.0.0",
        "patch_id": "patch_transaction_001",
        "source_score_id": score["score_id"],
        "source_fingerprint": score_fingerprint(score),
        "instruction": "Apply a bounded test edit.",
        "target_scope": {"measures": [1], "staffs": [1]},
        "protected_scope": {"staffs": [2]},
        "preconditions": [],
        "operations": [
            {
                "operation_id": "op_001",
                "type": op_type,
                "selector": {"event_ids": event_ids},
                "arguments": arguments or {"semitones": 2},
                "preconditions": [],
                "expected_change_count": len(event_ids),
            }
        ],
        "expected_effects": [{"type": "preserve_duration"}] if op_type == "transpose" else [],
        "provenance": {"provider": "mock", "model": "mock", "seed": 42},
    }


def test_transaction_commits_valid_transpose_and_roundtrip(two_staff_score: dict) -> None:
    before = copy.deepcopy(two_staff_score)
    result = PatchTransaction().execute(two_staff_score, make_patch(two_staff_score))
    assert result.committed is True
    assert result.report.status == "valid"
    assert [event["pitch"] for event in result.score_document["measures"][0]["events"][:4]] == ["D4", "E4", "F#4", "G4"]
    assert result.report.checks["protected_scope"]["checks"]["preservation_rate"] == 1.0
    assert result.report.checks["musicxml_roundtrip"]["validator_valid"] is True
    assert two_staff_score == before


def test_transaction_accepts_full_scope_non_default_persistent_dynamic(two_staff_score: dict) -> None:
    event_ids = [
        event["event_id"]
        for measure in two_staff_score["measures"]
        for event in measure["events"]
    ]
    patch = make_patch(
        two_staff_score,
        event_ids=event_ids,
        op_type="set_dynamic",
        arguments={"dynamic": "ff"},
    )
    patch["target_scope"] = {"measures": [1, 2]}
    patch["protected_scope"] = {}

    result = PatchTransaction().execute(two_staff_score, patch, dry_run=True)

    assert result.report.status == "valid"
    assert result.report.errors == []
    assert result.diff["changed_element_count"] == len(event_ids)
    assert result.report.checks["roundtrip_fidelity"]["checks"]["field_mismatches"] == []
    assert result.musicxml.count("<ff/>") == 2


def test_host_beams_outside_target_are_preserved_without_protected_scope_false_positive(
    two_staff_score: dict,
) -> None:
    score = copy.deepcopy(two_staff_score)
    score["metadata"]["source"] = "musescore_bridge"
    second_measure = score["measures"][1]
    second_measure["events"] = [
        event for event in second_measure["events"] if event["staff"] == "left_hand"
    ]
    custom_beams = ["begin", "continue", "continue", "end"] * 2
    for index in range(8):
        second_measure["events"].append(
            {
                "event_id": f"m2_host_beam_{index + 1}",
                "type": "note",
                "pitch": "C5",
                "duration": "eighth",
                "offset": index * 0.5,
                "voice": 1,
                "staff": "right_hand",
                "tie": None,
                "slur": None,
                "accidental": "",
                "dynamic": "mf",
                "articulations": [],
                "beam": {"number": 1, "value": custom_beams[index]},
                "selected": False,
            }
        )
    score = normalize_score_document(score)
    original_beams = [
        copy.deepcopy(event.get("beam"))
        for event in score["measures"][1]["events"]
        if event["staff"] == "right_hand"
    ]

    result = PatchTransaction().execute(score, make_patch(score), dry_run=True)

    assert result.report.errors == []
    assert result.rollback_reason is None
    assert result.diff["changed_element_count"] == 4
    assert result.report.checks["protected_scope"]["checks"]["unexpected_changed_elements"] == 0
    proposed_beams = [
        copy.deepcopy(event.get("beam"))
        for event in result.history_entry["after_score_document"]["measures"][1]["events"]
        if event["staff"] == "right_hand"
    ]
    assert proposed_beams == original_beams


def test_generated_beam_materialization_does_not_count_as_user_edit(two_staff_score: dict) -> None:
    score = copy.deepcopy(two_staff_score)
    score["metadata"]["source"] = "generated"
    second_measure = score["measures"][1]
    second_measure["events"] = [
        event for event in second_measure["events"] if event["staff"] == "left_hand"
    ]
    for index in range(8):
        second_measure["events"].append(
            {
                "event_id": f"m2_generated_eighth_{index + 1}",
                "type": "note",
                "pitch": "C5",
                "duration": "eighth",
                "offset": index * 0.5,
                "voice": 1,
                "staff": "right_hand",
                "tie": None,
                "slur": None,
                "accidental": "",
                "dynamic": "mf",
                "articulations": [],
                "selected": False,
            }
        )
    score = normalize_score_document(score)

    result = PatchTransaction().execute(score, make_patch(score), dry_run=True)

    assert result.report.errors == []
    assert result.rollback_reason is None
    assert result.diff["changed_element_count"] == 4
    assert result.report.checks["protected_scope"]["checks"]["unexpected_changed_elements"] == 0
    assert any(
        event.get("beam")
        for event in result.history_entry["after_score_document"]["measures"][1]["events"]
        if event["staff"] == "right_hand"
    )


def test_protected_event_attempt_is_rejected_before_apply(two_staff_score: dict) -> None:
    patch = make_patch(two_staff_score, event_ids=["m1_lh_1"])
    result = PatchTransaction().execute(two_staff_score, patch)
    assert result.committed is False
    assert result.rollback_reason == "pre-apply validation failed"
    assert "E11" in {item.code for item in result.report.errors}
    assert result.post_fingerprint == result.source_fingerprint


def test_source_drift_rolls_back(two_staff_score: dict) -> None:
    patch = make_patch(two_staff_score)
    changed = copy.deepcopy(two_staff_score)
    changed["measures"][0]["events"][0]["pitch"] = "B4"
    result = PatchTransaction().execute(changed, patch)
    assert result.committed is False
    assert any("source_fingerprint" in item.message for item in result.report.errors)


def test_duration_overflow_rolls_back_without_partial_state(two_staff_score: dict) -> None:
    patch = make_patch(
        two_staff_score,
        event_ids=["m1_rh_4"],
        op_type="set_duration",
        arguments={"duration": "whole"},
    )
    result = PatchTransaction().execute(two_staff_score, patch)
    assert result.committed is False
    assert result.rollback_reason == "post-apply validation failed"
    assert "E07" in {item.code for item in result.report.errors}
    assert result.score_document["measures"][0]["events"][3]["duration"] == "quarter"


def test_dry_run_returns_preview_diff_but_does_not_commit(two_staff_score: dict) -> None:
    result = PatchTransaction().execute(two_staff_score, make_patch(two_staff_score), dry_run=True)
    assert result.committed is False
    assert result.rollback_reason is None
    assert result.diff["changed_element_count"] == 4
    assert result.history_entry is not None
    assert score_fingerprint(result.score_document) == score_fingerprint(two_staff_score)


def test_patch_level_undo_and_redo(two_staff_score: dict) -> None:
    history = UndoManager()
    transaction = PatchTransaction(undo_manager=history)
    result = transaction.execute(two_staff_score, make_patch(two_staff_score))
    assert len(history.done) == 1
    undone = history.undo(result.score_document)
    redone = history.redo(undone)
    assert score_fingerprint(undone) == score_fingerprint(two_staff_score)
    assert score_fingerprint(redone) == result.post_fingerprint


def test_global_signature_change_requires_whole_score(two_staff_score: dict) -> None:
    patch = make_patch(two_staff_score, event_ids=[])
    patch["operations"][0] = {
        "operation_id": "op_meter",
        "type": "change_time_signature",
        "selector": {},
        "arguments": {"meter": "3/4"},
        "preconditions": [],
        "expected_change_count": None,
    }
    result = PatchTransaction().execute(two_staff_score, patch)
    assert result.committed is False
    assert "E05" in {item.code for item in result.report.errors}


def test_sparse_workbench_score_accepts_exporter_materialized_rests() -> None:
    score = new_score_document(measures=4)
    score["score_id"] = "score_sparse_workbench"
    score["measures"][0]["events"] = [
        {
            "event_id": "m1_note_1",
            "type": "note",
            "pitch": "C4",
            "duration": "quarter",
            "offset": 0.0,
            "voice": 1,
            "staff": "right_hand",
            "tie": None,
            "slur": None,
            "accidental": "",
            "dynamic": "mf",
            "articulations": [],
            "selected": False,
        }
    ]
    score = normalize_score_document(score)
    patch = make_patch(score, event_ids=["m1_note_1"])

    result = PatchTransaction().execute(score, patch, dry_run=True)

    assert result.report.status == "warning"
    assert result.report.errors == []
    assert result.rollback_reason is None
    fidelity = result.report.checks["roundtrip_fidelity"]["checks"]
    assert fidelity["missing_event_ids"] == []
    assert fidelity["added_event_ids"] == []
    assert result.history_entry["after_score_document"]["measures"][1]["events"] == []

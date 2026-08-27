from __future__ import annotations

import copy

from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.execution.patch_repair import deterministic_repair
from sera_edit.validation.schema_validator import validate_patch_schema


def _patch(score: dict) -> dict:
    return {
        "schema_version": "1.0.0",
        "patch_id": "patch_schema_001",
        "source_score_id": score["score_id"],
        "source_fingerprint": score_fingerprint(score),
        "instruction": "Transpose measure 1 right hand up a major second.",
        "target_scope": {"measures": [1], "staffs": [1]},
        "protected_scope": {"staffs": [2]},
        "preconditions": [],
        "operations": [
            {
                "operation_id": "op_001",
                "type": "transpose",
                "selector": {"event_ids": [f"m1_rh_{index}" for index in range(1, 5)]},
                "arguments": {"semitones": 2},
                "preconditions": [],
                "expected_change_count": 4,
            }
        ],
        "expected_effects": [{"type": "preserve_duration"}],
        "provenance": {"provider": "mock", "model": "mock"},
    }


def test_valid_patch_schema(two_staff_score: dict) -> None:
    report = validate_patch_schema(_patch(two_staff_score))
    assert report.status == "valid"


def test_unknown_operation_is_explicitly_unsupported(two_staff_score: dict) -> None:
    patch = _patch(two_staff_score)
    patch["operations"][0]["type"] = "compose_better_music"
    report = validate_patch_schema(patch)
    assert report.status == "unsupported"
    assert {item.code for item in report.errors} == {"E19"}


def test_unknown_patch_field_is_rejected(two_staff_score: dict) -> None:
    patch = _patch(two_staff_score)
    patch["secret_full_score_rewrite"] = True
    report = validate_patch_schema(patch)
    assert report.status == "invalid"
    assert any("unknown patch field" in item.message for item in report.errors)


def test_deterministic_repair_does_not_infer_music(two_staff_score: dict) -> None:
    patch = _patch(two_staff_score)
    patch.pop("schema_version")
    patch["operations"][0]["type"] = "TRANSPOSE"
    patch["operations"][0]["selector"] = {"event_id": "m1_rh_1"}
    result = deterministic_repair(patch)
    assert result.repaired["schema_version"] == "1.0.0"
    assert result.repaired["operations"][0]["type"] == "transpose"
    assert result.repaired["operations"][0]["selector"]["event_ids"] == ["m1_rh_1"]


def test_bad_fingerprint_is_rejected(two_staff_score: dict) -> None:
    patch = copy.deepcopy(_patch(two_staff_score))
    patch["source_fingerprint"] = "sha256:not-a-digest"
    assert validate_patch_schema(patch).status == "invalid"

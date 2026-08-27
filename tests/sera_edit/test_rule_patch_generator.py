from __future__ import annotations

from sera_edit.generation.rule_patch_generator import generate_rule_patch


def test_generates_chinese_transpose_patch_for_selected_events(two_staff_score: dict) -> None:
    result = generate_rule_patch(
        two_staff_score,
        "将第一小节右手升高大二度，并保持节奏不变。",
        {"measures": [1], "staffs": [1]},
        {"staffs": [2]},
    )

    assert result.status == "generated"
    assert result.patch is not None
    assert result.patch["operations"][0]["type"] == "transpose"
    assert result.patch["operations"][0]["arguments"] == {"semitones": 2}
    assert result.patch["operations"][0]["selector"]["event_ids"] == [
        "m1_rh_1",
        "m1_rh_2",
        "m1_rh_3",
        "m1_rh_4",
    ]
    assert result.patch["provenance"]["formal_experiment_eligible"] is False


def test_generates_compound_dynamic_and_articulation_patch(two_staff_score: dict) -> None:
    result = generate_rule_patch(
        two_staff_score,
        "Set the selected notes to forte and staccato.",
        {"event_ids": ["m1_rh_1", "m1_rh_2"]},
    )

    assert result.status == "generated"
    assert result.patch is not None
    assert [operation["type"] for operation in result.patch["operations"]] == [
        "set_dynamic",
        "set_articulation",
    ]
    assert result.patch["expected_effects"] == [
        {"type": "preserve_duration"},
        {"type": "preserve_pitch"},
    ]


def test_chinese_preserve_pitch_does_not_add_tenuto(two_staff_score: dict) -> None:
    result = generate_rule_patch(
        two_staff_score,
        "只将第1小节第三个音改为强奏，并保持音高与时值。",
        {"measures": [1], "staffs": [1]},
        {"staffs": [2]},
    )

    assert result.status == "generated"
    assert result.patch is not None
    assert [operation["type"] for operation in result.patch["operations"]] == ["set_dynamic"]
    assert result.patch["operations"][0]["selector"]["event_ids"] == ["m1_rh_3"]


def test_generates_global_key_signature_patch_without_transposing_notes(two_staff_score: dict) -> None:
    result = generate_rule_patch(
        two_staff_score,
        "Change the score key signature to G major without transposing notes.",
        {"whole_score": True},
    )

    assert result.status == "generated"
    assert result.patch is not None
    assert result.patch["operations"] == [
        {
            "operation_id": "op_001",
            "type": "change_key_signature",
            "selector": {},
            "arguments": {"key": "G major"},
            "preconditions": [],
            "expected_change_count": None,
        }
    ]
    assert result.patch["expected_effects"] == [
        {"type": "preserve_duration"},
        {"type": "preserve_pitch"},
    ]


def test_promotes_host_measure_selection_for_explicit_chinese_global_key_edit(two_staff_score: dict) -> None:
    result = generate_rule_patch(
        two_staff_score,
        "将调号改为G major，但不要移调音符。",
        {"measures": [1, 2]},
    )

    assert result.status == "generated"
    assert result.patch is not None
    assert result.patch["target_scope"]["whole_score"] is True
    assert result.patch["target_scope"]["measures"] == []
    assert result.patch["operations"][0]["type"] == "change_key_signature"
    assert result.patch["operations"][0]["arguments"] == {"key": "G major"}
    assert result.patch["provenance"]["scope_resolution"] == "promoted_to_whole_score_for_global_key_signature"
    assert result.patch["provenance"]["requested_target_scope"]["measures"] == [1, 2]


def test_promotes_mixed_meter_rebar_from_host_measure_selection(two_staff_score: dict) -> None:
    result = generate_rule_patch(
        two_staff_score,
        (
            "Rebar the selected excerpt from 4/4 to 3/4 by removing the final quarter-note event "
            "from each staff in every measure; preserve every remaining pitch and duration."
        ),
        {"measures": [1, 2]},
    )

    assert result.status == "generated"
    assert result.patch is not None
    assert result.patch["target_scope"]["whole_score"] is True
    assert result.patch["target_scope"]["measures"] == []
    assert [operation["type"] for operation in result.patch["operations"]] == [
        "change_time_signature",
        "delete_event",
    ]
    assert result.patch["operations"][1]["selector"]["event_ids"] == [
        "m1_lh_4",
        "m1_rh_4",
        "m2_lh_4",
        "m2_rh_4",
    ]
    assert result.patch["provenance"]["scope_resolution"] == "promoted_to_whole_score_for_global_property"
    assert result.patch["provenance"]["requested_target_scope"]["measures"] == [1, 2]


def test_refuses_meter_duration_conflict(two_staff_score: dict) -> None:
    result = generate_rule_patch(
        two_staff_score,
        "改为5/8拍，同时保持全部时值不变。",
        {"whole_score": True},
    )

    assert result.status == "refused"
    assert result.patch is None
    assert result.reason is not None
    assert "durations" in result.reason


def test_unsupported_instruction_is_explicit(two_staff_score: dict) -> None:
    result = generate_rule_patch(two_staff_score, "让它更有海浪的感觉", {"measures": [1]})

    assert result.status == "unsupported"
    assert result.patch is None
    assert result.reason is not None
    assert "currently support" in result.reason


def test_compound_edit_targets_final_two_pitches_but_only_final_dynamic(two_staff_score: dict) -> None:
    result = generate_rule_patch(
        two_staff_score,
        "Transpose the final two notes of measure 2 staff 1 up a semitone and mark the final note forte.",
        {"measures": [2], "staffs": [1]},
        {"staffs": [2]},
    )

    assert result.status == "generated"
    assert result.patch is not None
    transpose, dynamic = result.patch["operations"]
    assert transpose["selector"]["event_ids"] == ["m2_rh_3", "m2_rh_4"]
    assert dynamic["selector"]["event_ids"] == ["m2_rh_4"]

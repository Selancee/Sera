from __future__ import annotations

import copy

from sera_edit.execution.diff_engine import score_diff
from sera_edit.validation.notation_relation_validator import validate_notation_relations


def test_diff_reports_only_changed_event(two_staff_score: dict) -> None:
    after = copy.deepcopy(two_staff_score)
    after["measures"][0]["events"][0]["dynamic"] = "ff"
    diff = score_diff(two_staff_score, after)
    assert diff["changed_element_count"] == 1
    assert diff["changed"][0]["changed_fields"] == ["dynamic"]


def test_broken_tie_is_rejected(two_staff_score: dict) -> None:
    score = copy.deepcopy(two_staff_score)
    score["measures"][0]["events"][0]["tie"] = "start"
    report = validate_notation_relations(score)
    assert report.status == "invalid"
    assert {item.code for item in report.errors} == {"E09"}


def test_balanced_slur_is_valid(two_staff_score: dict) -> None:
    score = copy.deepcopy(two_staff_score)
    score["measures"][0]["events"][0]["slur"] = "start"
    score["measures"][0]["events"][1]["slur"] = "stop"
    assert validate_notation_relations(score).status == "valid"


def test_score_diff_treats_equivalent_flat_key_spelling_as_unchanged(two_staff_score: dict) -> None:
    before = copy.deepcopy(two_staff_score)
    after = copy.deepcopy(two_staff_score)
    before["global"]["key"] = "B-flat major"
    after["global"]["key"] = "Bb major"
    assert score_diff(before, after)["global_changes"] == {}

from __future__ import annotations

import pytest

from sera_edit.domain.score_scope import ScoreScope


def test_scope_matches_measure_staff_voice(two_staff_score: dict) -> None:
    scope = ScoreScope.from_dict({"measures": [2], "staffs": [1], "voices": [1]})
    assert [item.event_id for item in scope.select(two_staff_score)] == [f"m2_rh_{index}" for index in range(1, 5)]


def test_scope_applies_explicit_exclusions(two_staff_score: dict) -> None:
    scope = ScoreScope.from_dict({"measures": [1], "exclude_event_ids": ["m1_rh_1"]})
    assert "m1_rh_1" not in {item.event_id for item in scope.select(two_staff_score)}
    assert len(scope.select(two_staff_score)) == 7


def test_scope_time_range_uses_exact_boundaries(two_staff_score: dict) -> None:
    scope = ScoreScope.from_dict({"measures": [1], "time_range": ["1/2", "2"]})
    assert {item.offset for item in scope.select(two_staff_score)} == {1}


def test_scope_rejects_reversed_time_range() -> None:
    with pytest.raises(ValueError, match="start"):
        ScoreScope.from_dict({"time_range": [2, 1]})

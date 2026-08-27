from __future__ import annotations

import copy

from sera_edit.domain.fingerprints import score_fingerprint


def test_fingerprint_ignores_volatile_fields(two_staff_score: dict) -> None:
    changed = copy.deepcopy(two_staff_score)
    changed["metadata"]["updated_at"] = "2099-01-01T00:00:00Z"
    changed["measures"][0]["events"][0]["selected"] = True
    assert score_fingerprint(changed) == score_fingerprint(two_staff_score)


def test_fingerprint_changes_for_musical_content(two_staff_score: dict) -> None:
    changed = copy.deepcopy(two_staff_score)
    changed["measures"][0]["events"][0]["pitch"] = "C#4"
    assert score_fingerprint(changed) != score_fingerprint(two_staff_score)


def test_fingerprint_normalizes_equivalent_flat_key_spelling(two_staff_score: dict) -> None:
    first = copy.deepcopy(two_staff_score)
    second = copy.deepcopy(two_staff_score)
    first["global"]["key"] = "B-flat major"
    second["global"]["key"] = "Bb major"
    assert score_fingerprint(first) == score_fingerprint(second)

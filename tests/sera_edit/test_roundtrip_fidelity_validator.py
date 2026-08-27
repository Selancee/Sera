from __future__ import annotations

import copy

from sera_edit.validation.roundtrip_fidelity_validator import validate_roundtrip_fidelity


def test_roundtrip_fidelity_accepts_supported_fields(two_staff_score: dict) -> None:
    imported = copy.deepcopy(two_staff_score)
    imported["metadata"]["updated_at"] = "different"
    assert validate_roundtrip_fidelity(two_staff_score, imported).status == "valid"


def test_roundtrip_fidelity_reports_lost_dynamic(two_staff_score: dict) -> None:
    imported = copy.deepcopy(two_staff_score)
    imported["measures"][0]["events"][0]["dynamic"] = "p"
    report = validate_roundtrip_fidelity(two_staff_score, imported)
    assert report.status == "invalid"
    assert report.errors[0].code == "E14"
    assert report.errors[0].details["fields"] == ["dynamic"]


def test_roundtrip_fidelity_reports_added_event(two_staff_score: dict) -> None:
    imported = copy.deepcopy(two_staff_score)
    extra = copy.deepcopy(imported["measures"][0]["events"][0])
    extra["event_id"] = "unexpected_rest"
    extra.update({"type": "rest", "pitch": "", "offset": 0.5})
    imported["measures"][0]["events"].append(extra)
    report = validate_roundtrip_fidelity(two_staff_score, imported)
    assert "unexpected_rest" in report.checks["added_event_ids"]


def test_roundtrip_fidelity_accepts_equivalent_flat_key_spelling(two_staff_score: dict) -> None:
    source = copy.deepcopy(two_staff_score)
    imported = copy.deepcopy(two_staff_score)
    source["global"]["key"] = "B-flat major"
    imported["global"]["key"] = "Bb major"
    assert validate_roundtrip_fidelity(source, imported).status == "valid"


def test_roundtrip_fidelity_reports_changed_beam(two_staff_score: dict) -> None:
    source = two_staff_score
    imported = copy.deepcopy(source)
    imported["measures"][0]["events"][0]["beam"] = {"number": 1, "value": "begin"}
    report = validate_roundtrip_fidelity(source, imported)
    assert "E14" in {issue.code for issue in report.errors}
    assert report.checks["field_mismatches"][0]["fields"] == ["beam"]

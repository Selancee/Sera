import copy

from sera_edit.validation.semantic_precondition_validator import validate_postconditions


def test_dynamic_postcondition_checks_value_and_missing_event(two_staff_score):
    after = copy.deepcopy(two_staff_score)
    effect = ({"type": "dynamic_equals", "event_id": "m1_rh_1", "value": "f"},)
    assert validate_postconditions(two_staff_score, after, effect).errors[0].code == "E15"
    next(e for e in after["measures"][0]["events"] if e["event_id"] == "m1_rh_1")["dynamic"] = "f"
    assert not validate_postconditions(two_staff_score, after, effect).errors
    after["measures"][0]["events"] = [e for e in after["measures"][0]["events"] if e["event_id"] != "m1_rh_1"]
    assert validate_postconditions(two_staff_score, after, effect).errors[0].code == "E15"


def test_dynamic_postcondition_without_selector_is_explicitly_unsupported(two_staff_score):
    report = validate_postconditions(two_staff_score, two_staff_score, ({"type": "dynamic_equals", "value": "f"},))
    assert report.unsupported
    assert report.errors[0].code == "E19"

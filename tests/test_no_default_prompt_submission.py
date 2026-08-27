from backend.services.prompt_control_resolver import resolve_prompt_controls


def test_empty_prompt_stays_empty_and_does_not_insert_legacy_default() -> None:
    resolution = resolve_prompt_controls(
        "",
        {"style": "romantic", "key": "A minor", "length_measures": 8},
        {"prompt_priority": True, "allow_ui_defaults": True},
        {"style": "explicit", "key": "explicit", "length_measures": "explicit"},
    )

    assert resolution["raw_prompt"] == ""
    assert resolution["intent_source"] == "control_only_intent"
    assert "romantic piano nocturne" not in resolution["raw_prompt"].lower()
    assert resolution["source_prompt_terms"] == []
    assert {item["field"] for item in resolution["source_control_terms"]} >= {"style", "key", "length_measures"}

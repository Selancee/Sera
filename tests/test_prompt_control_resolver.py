from backend.services.prompt_control_resolver import resolve_prompt_controls


def test_prompt_wins_over_default_ui_style_and_length() -> None:
    prompt = "\u8d5b\u535a\u670b\u514b\u94a2\u7434\uff0c\u673a\u68b0\u611f\uff0c\u51b7\u8272\uff0c\u5207\u5206\u8282\u594f\uff0c\u91cd\u590d\u4f4e\u97f3\uff0c8\u5c0f\u8282"
    resolution = resolve_prompt_controls(
        prompt,
        {"style": "romantic", "texture": "melody_accompaniment", "length": 16},
        {"prompt_priority": True, "allow_ui_defaults": True},
        {"style": "default", "texture": "default", "length": "default"},
    )

    assert resolution["resolved_controls"]["style"] == "cyberpunk"
    assert resolution["resolved_controls"]["texture"] == "ostinato"
    assert resolution["resolved_controls"]["length_measures"] == 8
    conflict_fields = {item["field"] for item in resolution["conflicts"]}
    assert {"style", "texture", "length_measures"}.issubset(conflict_fields)


def test_explicit_ui_key_wins_over_prompt_key_conflict() -> None:
    resolution = resolve_prompt_controls(
        "Compose a short piano phrase in C major.",
        {"key": "A minor", "length": 16},
        {"prompt_priority": True, "allow_ui_defaults": True},
        {"key": "explicit", "length": "default"},
    )

    assert resolution["resolved_controls"]["key"] == "A minor"
    key_conflict = next(item for item in resolution["conflicts"] if item["field"] == "key")
    assert key_conflict["resolution"] == "ui_wins"
    assert key_conflict["ui_source"] == "explicit"


def test_default_ui_key_yields_to_prompt_key_conflict() -> None:
    resolution = resolve_prompt_controls(
        "Compose a short piano phrase in C major.",
        {"key": "A minor", "length": 16},
        {"prompt_priority": True, "allow_ui_defaults": True},
        {"key": "default", "length": "default"},
    )

    assert resolution["resolved_controls"]["key"] == "C major"
    key_conflict = next(item for item in resolution["conflicts"] if item["field"] == "key")
    assert key_conflict["resolution"] == "prompt_wins"
    assert key_conflict["ui_source"] == "default"

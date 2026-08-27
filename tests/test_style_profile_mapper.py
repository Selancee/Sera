from backend.generation.musicality.style_profile_mapper import map_style_profile


def test_cyberpunk_style_profile_maps_to_electronic_controls():
    mapping = map_style_profile("cyberpunk piano passage", "classical")

    assert mapping["style"] == "custom"
    assert mapping["base_style"] == "electronic"
    assert "cyberpunk" in mapping["custom_style_tags"]
    profile = mapping["style_profile"]
    assert profile["texture"] == "ostinato"
    assert profile["accompaniment_style"] == "repeating_bass"
    assert profile["harmony_flavor"] == "minor_modal"

from backend.generation.musicality.harmony_profile import build_harmony_profile


def test_cyberpunk_maps_to_electronic_modal_pedal_logic() -> None:
    profile = build_harmony_profile({"base_style": "electronic", "custom_style_tags": ["cyberpunk"]}, "A minor", "minor", "intermediate")

    assert profile["style"] == "electronic"
    assert "pedal_point" in profile["vocabulary"]
    assert "ostinato_bass" in profile["vocabulary"]

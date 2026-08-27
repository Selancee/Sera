from backend.pipeline import SeraPipeline


def test_empty_prompt_with_controls_uses_control_only_intent(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "",
        generator_mode="rule_based",
        ui_controls={"style": "cyberpunk", "key": "A minor", "meter": "4/4", "texture": "ostinato", "length_measures": 8},
        ui_control_sources={"style": "explicit", "key": "explicit", "meter": "explicit", "texture": "explicit", "length_measures": "explicit"},
        musicality_controls={"variation_seed": "control-only-v096"},
    )

    assert result["raw_prompt"] == ""
    assert result["prompt_control_resolution"]["intent_source"] == "control_only_intent"
    assert result["prompt_control_resolution"]["control_only_intent"] is True
    assert result["generation_metadata"]["harmony_profile"]["style"] == "electronic"
    assert result["validation"]["valid"] is True

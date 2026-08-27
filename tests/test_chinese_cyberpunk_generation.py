from backend.pipeline import SeraPipeline


def test_chinese_cyberpunk_generation_preserves_prompt_and_drives_plan() -> None:
    prompt = "\u8d5b\u535a\u670b\u514b\u94a2\u7434\uff0c\u673a\u68b0\u611f\uff0c\u51b7\u8272\uff0c\u5207\u5206\u8282\u594f\uff0c\u91cd\u590d\u4f4e\u97f3\uff0c8\u5c0f\u8282"
    result = SeraPipeline().generate(
        prompt,
        generator_mode="rule_based",
        ui_controls={"style": "romantic", "texture": "melody_accompaniment", "length": 16},
        ui_control_sources={"style": "default", "texture": "default", "length": "default"},
        control_policy={"prompt_priority": True, "allow_ui_defaults": True},
        musicality_controls={"variation_seed": "test-chinese-cyberpunk"},
    )

    assert result["raw_prompt"] == prompt
    assert result["intent"]["style"] == "custom"
    assert result["intent"]["base_style"] == "electronic"
    assert "cyberpunk" in result["intent"]["custom_style_tags"]
    assert result["plan"]["global_plan"]["texture"] == "ostinato"
    assert result["plan"]["global_plan"]["accompaniment_style"] == "repeating_bass"
    assert result["plan"]["global_plan"]["harmony_flavor"] == "minor_modal"
    assert result["plan"]["measures"][0]["texture"] == "ostinato"
    assert "ostinato" in result["plan"]["measures"][0]["rhythm"]
    assert result["generation_metadata"]["generation_profile"]["texture"] == "ostinato"
    assert result["prompt_control_resolution"]["prompt_plan_alignment_score"] >= 0.7

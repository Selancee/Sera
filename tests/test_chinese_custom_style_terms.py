from backend.agents.prompt_understanding_agent import PromptUnderstandingAgent


def test_chinese_cyberpunk_prompt_maps_to_custom_electronic_profile() -> None:
    prompt = "\u8d5b\u535a\u670b\u514b\u94a2\u7434\uff0c\u673a\u68b0\u611f\uff0c\u51b7\u8272\uff0c\u5207\u5206\u8282\u594f\uff0c\u91cd\u590d\u4f4e\u97f3\uff0c8\u5c0f\u8282"
    intent = PromptUnderstandingAgent().understand(prompt)

    assert intent.style == "custom"
    assert intent.base_style == "electronic"
    assert "cyberpunk" in intent.custom_style_tags
    assert {"mechanical", "cold", "futuristic"} & set(intent.custom_style_tags)
    assert intent.style_profile["texture"] == "ostinato"
    assert intent.style_profile["accompaniment_style"] == "repeating_bass"
    assert "minor" in intent.style_profile["harmony_flavor"]
    assert "\u8d5b\u535a\u670b\u514b" in intent.source_prompt_terms

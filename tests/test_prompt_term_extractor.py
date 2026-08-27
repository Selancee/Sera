from backend.services.prompt_term_extractor import extract_prompt_terms


def test_extracts_chinese_cyberpunk_terms() -> None:
    prompt = "\u8d5b\u535a\u670b\u514b\u94a2\u7434\uff0c\u673a\u68b0\u611f\uff0c\u51b7\u8272\uff0c\u5207\u5206\u8282\u594f\uff0c\u91cd\u590d\u4f4e\u97f3\uff0c8\u5c0f\u8282"
    payload = extract_prompt_terms(prompt)
    normalized = {item["normalized"] for item in payload["prompt_terms"]}

    assert payload["language"] == "zh-CN"
    assert {"cyberpunk", "mechanical", "cold", "syncopation", "repeating_bass", "piano", "8"}.issubset(normalized)
    assert "\u8d5b\u535a\u670b\u514b" in payload["source_prompt_terms"]

from backend.pipeline import SeraPipeline


def test_generated_musicxml_contains_beams_for_eighth_notes(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate("Compose an 8 measure anime piano theme with eighth notes.", generator_mode="rule_based")

    assert "<type>eighth</type>" in result["musicxml"]
    assert "<beam number=\"1\">begin</beam>" in result["musicxml"]
    assert "<beam number=\"1\">end</beam>" in result["musicxml"]


def test_style_outputs_with_short_notes_include_beam_tags(tmp_path) -> None:
    pipeline = SeraPipeline(tmp_path)
    prompts = [
        "cyberpunk piano passage with syncopated eighth ostinato, 8 measures",
        "anime style bright lyrical piano theme, 8 measures",
        "romantic flowing nocturne piano with eighth motion, 8 measures",
        "Chinese pentatonic piano with eighth-note motion, 8 measures",
    ]

    for prompt in prompts:
        result = pipeline.generate(prompt, generator_mode="rule_based")
        if "<type>eighth</type>" in result["musicxml"] or "<type>16th</type>" in result["musicxml"]:
            assert "<beam number=\"1\">" in result["musicxml"]

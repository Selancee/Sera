from backend.pipeline import SeraPipeline


def test_explicit_ui_key_controls_generated_score(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "Compose an 8 measure piano phrase in C major.",
        generator_mode="rule_based",
        ui_controls={
            "style": "romantic",
            "instrument": "piano",
            "key": "A minor",
            "meter": "4/4",
            "length_measures": 8,
        },
        ui_control_sources={
            "style": "default",
            "instrument": "default",
            "key": "explicit",
            "meter": "default",
            "length_measures": "explicit",
        },
        control_policy={"prompt_priority": True, "allow_ui_defaults": True},
        musicality_controls={"variation_seed": "explicit-a-minor-test"},
    )

    assert result["intent"]["key"] == "A minor"
    assert result["prompt_control_resolution"]["resolved_controls"]["key"] == "A minor"
    assert result["score_document"]["global"]["key"] == "A minor"
    assert result["generation_metadata"]["generation_profile"]["key"] == "A minor"
    assert "<mode>minor</mode>" in result["musicxml"]

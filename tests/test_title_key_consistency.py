from backend.pipeline import SeraPipeline


def test_prompt_c_major_ui_a_minor_does_not_leave_c_major_title(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "Compose an 8 measure piano phrase in C major.",
        generator_mode="rule_based",
        ui_controls={"key": "A minor", "style": "romantic", "instrument": "piano", "meter": "4/4", "length_measures": 8},
        ui_control_sources={"key": "explicit", "style": "default", "instrument": "default", "meter": "default", "length_measures": "explicit"},
        control_policy={"prompt_priority": True, "allow_ui_defaults": True},
        musicality_controls={"variation_seed": "v095-title-key"},
    )

    assert result["intent"]["key"] == "A minor"
    assert result["score_document"]["global"]["key"] == "A minor"
    assert "C major" not in result["score_document"]["title"]
    assert "C major" not in result["intent"]["title"]
    assert "<work-title>Sera Piano Sketch</work-title>" in result["musicxml"]
    assert result["key_consistency_report"]["stale_key_in_title"] is False


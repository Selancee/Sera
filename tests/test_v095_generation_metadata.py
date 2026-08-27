from backend.pipeline import SeraPipeline


def test_v095_generation_metadata_contains_sync_and_melody_reports(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "Compose an 8 measure piano phrase in C major.",
        generator_mode="rule_based",
        ui_controls={"key": "A minor", "length_measures": 8},
        ui_control_sources={"key": "explicit", "length_measures": "explicit"},
        musicality_controls={"variation_seed": "v095-metadata"},
    )
    metadata = result["generation_metadata"]

    assert metadata["metadata_sync_report"]["resolved_key"] == "A minor"
    assert metadata["key_consistency_report"]["valid"] is True
    assert metadata["melody_line_report"]["primary_melody"]["staff"] == "right_hand"
    assert metadata["cross_measure_melodic_grammar_report"]["source"] == "primary_melody_line"
    assert result["score_document"]["metadata"]["generation_metadata"]["melody_line_report"]["primary_melody"]["staff"] == "right_hand"


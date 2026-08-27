from backend.pipeline import SeraPipeline


def test_v093_generation_pipeline_has_real_source_reports(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate("Compose an 8 measure cyberpunk piano passage.", generator_mode="rule_based")

    assert result["score_document"]["schema_version"] == "0.6"
    assert result["preview_render"]["renderer"] in {"musescore_cli", "verovio", "unavailable"}
    assert result["generation_metadata"]["notation_validation_report"]["valid"] is True
    assert result["generation_metadata"]["musicality_validation_report"]["left_hand_activity"] >= 0.6
    assert result["generation_metadata"]["musicality_validation_report"]["quarter_note_dominance"] <= 0.7

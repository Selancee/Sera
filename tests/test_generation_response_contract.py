from backend.pipeline import SeraPipeline


def test_generate_response_contains_v092_authoritative_contract(tmp_path):
    pipeline = SeraPipeline(tmp_path)

    result = pipeline.generate("Compose an 8 measure cyberpunk piano passage.", generator_mode="rule_based")

    assert result["score_document"]["schema_version"] == "0.6"
    assert result["musicxml"].lstrip().startswith("<?xml")
    assert result["midi_url"].endswith("/midi")
    assert result["exports"]["musicxml"].endswith("/musicxml")
    assert "consistency_report" in result
    assert "generation_metadata" in result
    assert result["generation_metadata"]["generation_profile"]["style"] == "custom"
    assert "cyberpunk" in result["generation_metadata"]["generation_profile"]["custom_style_tags"]

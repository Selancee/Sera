from backend.pipeline import SeraPipeline


def test_pipeline_marks_final_cadence_on_score_document(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate("Compose an 8 measure romantic piano piece with a clear ending.", generator_mode="rule_based")

    assert result["score_document"]["measures"][-1]["cadence"] in {"authentic", "modal_pentatonic_ending"}
    assert result["generation_metadata"]["notation_validation_report"]["valid"] is True

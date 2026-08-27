from backend.pipeline import SeraPipeline


def test_candidate_generation_records_selected_and_rejected_candidates(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "Compose an 8 measure pop piano theme.",
        generator_mode="rule_based",
        musicality_controls={"variation_seed": "candidate-v096"},
        candidate_count=4,
    )

    candidate = result["generation_metadata"]["candidate_generation"]
    assert candidate["candidate_count"] == 4
    assert 0 <= candidate["selected_candidate_index"] < 4
    assert len(candidate["rejected_candidates"]) == 3
    assert result["generation_metadata"]["candidate_rank_report"]["score"] == candidate["selected_candidate_score"]


def test_fixed_run_seed_reproduces_candidate_set_and_selection(tmp_path) -> None:
    pipeline = SeraPipeline(tmp_path)
    controls = {"variation_seed": "fixed-candidate-v096"}
    first = pipeline.generate("Compose an 8 measure anime piano theme.", generator_mode="rule_based", musicality_controls=controls)
    second = pipeline.generate("Compose an 8 measure anime piano theme.", generator_mode="rule_based", musicality_controls=controls)

    assert first["generation_metadata"]["candidate_generation"] == second["generation_metadata"]["candidate_generation"]
    assert first["musicxml"] == second["musicxml"]

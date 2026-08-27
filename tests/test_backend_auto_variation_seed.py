from backend.pipeline import SeraPipeline


def test_backend_auto_generates_distinct_run_seeds(tmp_path) -> None:
    pipeline = SeraPipeline(tmp_path)

    first = pipeline.generate("Compose an 8 measure cyberpunk piano passage.", generator_mode="rule_based")
    second = pipeline.generate("Compose an 8 measure cyberpunk piano passage.", generator_mode="rule_based")

    first_profile = first["generation_metadata"]["generation_profile"]
    second_profile = second["generation_metadata"]["generation_profile"]
    assert first_profile["run_seed"]
    assert second_profile["run_seed"]
    assert first_profile["seed_source"] == "backend_auto"
    assert first_profile["run_seed"] != second_profile["run_seed"]
    assert first["metadata"]["run_seed"] == first_profile["run_seed"]


def test_fixed_seed_remains_reproducible(tmp_path) -> None:
    pipeline = SeraPipeline(tmp_path)
    controls = {"variation_seed": "fixed-v094-seed"}

    first = pipeline.generate("Compose an 8 measure anime piano theme.", generator_mode="rule_based", musicality_controls=controls)
    second = pipeline.generate("Compose an 8 measure anime piano theme.", generator_mode="rule_based", musicality_controls=controls)

    assert first["generation_metadata"]["generation_profile"]["run_seed"] == second["generation_metadata"]["generation_profile"]["run_seed"]
    assert first["musicxml"] == second["musicxml"]

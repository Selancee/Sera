from backend.generation.seed_service import create_run_seed, create_variant_id, make_seeded_rng


def test_create_run_seed_auto_differs_between_calls() -> None:
    first = create_run_seed("same prompt", {})
    second = create_run_seed("same prompt", {})

    assert first
    assert second
    assert first != second


def test_create_run_seed_explicit_is_reproducible() -> None:
    first = create_run_seed("prompt", {"variation_seed": "fixed-seed"})
    second = create_run_seed("other prompt", {"variation_seed": "fixed-seed"})

    assert first == second
    assert create_variant_id(first).startswith("variant_")
    assert make_seeded_rng(first, "melody").random() == make_seeded_rng(first, "melody").random()

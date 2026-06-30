from evaluation.metrics.prompt_alignment_edit_metrics import prompt_alignment_edit_metrics


def test_prompt_alignment_edit_metrics_penalizes_constraint_breaks() -> None:
    patch = {
        "target_range": {"start_measure": 1, "end_measure": 2},
        "operations": [{"type": "update_harmony"}],
    }
    metrics = prompt_alignment_edit_metrics(
        "preserve harmony but make it more lyrical",
        {"start_measure": 1, "end_measure": 2},
        {"preserve_harmony": True},
        patch,
        {"valid_musicxml": True},
    )

    assert metrics["selection_respect_score"] == 1.0
    assert metrics["constraint_respect_score"] < 1.0
    assert 0.0 <= metrics["overall_prompt_alignment_edit_score"] <= 1.0


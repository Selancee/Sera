import json
from pathlib import Path

from backend.generation.model_generator import ModelGenerator


def test_model_lab_falls_back_to_recorded_samples(tmp_path: Path) -> None:
    run_dir = tmp_path / "docs" / "training_runs" / "autodl_test"
    run_dir.mkdir(parents=True)
    (run_dir / "training_metrics.json").write_text(
        json.dumps(
            {
                "token_rows": 2,
                "sequence_chunks": 4,
                "vocab_size": 8,
                "history": [{"epoch": 1, "train_loss": 1.0, "val_loss": 0.9}],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "samples.json").write_text(
        json.dumps(
            [
                {
                    "prompt": "romantic piano",
                    "tokens": ["<bos>", "<prompt>", "romantic", "<score>", "<score-partwise version=\"3.1\">"],
                }
            ]
        ),
        encoding="utf-8",
    )

    model = ModelGenerator(tmp_path)
    status = model.status()
    sample = model.sample_tokens("romantic piano nocturne")

    assert status["available"] is False
    assert status["mode"] == "recorded_sample"
    assert status["run_id"] == "autodl_test"
    assert sample["model_loaded"] is False
    assert sample["tokens"][-1] == '<score-partwise version="3.1">'
    assert "score-partwise" in sample["musicxml_preview"]

import json
from pathlib import Path

from backend.generation.model_generator import ModelGenerator
from backend.pipeline import SeraPipeline


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


def test_model_lab_reports_default_checkpoint_location(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SERA_SYMBOLIC_MODEL_CHECKPOINT", raising=False)
    monkeypatch.delenv("SERA_SYMBOLIC_MODEL_DIR", raising=False)

    model = ModelGenerator(tmp_path)
    status = model.status()

    expected = tmp_path / "models" / "sera_symbolic_small"
    assert status["expected_model_dir"] == str(expected)
    assert str(expected / "model.pt") in status["checkpoint_candidates"]
    assert status["mode"] == "recorded_sample"


def test_pipeline_uses_configured_model_backend_with_safe_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SERA_GENERATOR_BACKEND", "model")
    monkeypatch.setenv("SERA_SYMBOLIC_MODEL_DIR", str(tmp_path / "models" / "sera_symbolic_small"))

    pipeline = SeraPipeline(tmp_path)
    status = pipeline.symbolic_model_status()
    result = pipeline.generate("Create an 8 bar calm piano sketch in C major.")

    assert status["generator_backend"] == "model"
    assert result["validation"]["valid"] is True
    assert Path(result["artifacts"]["musicxml_path"]).exists()


def test_main_generation_uses_checkpoint_conditioning(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SERA_GENERATOR_BACKEND", "model")
    monkeypatch.setenv("SERA_ACTIVE_SYMBOLIC_MODEL", "unit_test_model")

    pipeline = SeraPipeline(tmp_path)
    monkeypatch.setattr(
        pipeline.generator.model_generator,
        "status",
        lambda: {
            "available": True,
            "mode": "checkpoint",
            "checkpoint_path": str(tmp_path / "models" / "unit_test_model" / "model.pt"),
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        pipeline.generator.model_generator,
        "_sample_from_checkpoint",
        lambda prompt, max_tokens, status: {
            "mode": "checkpoint",
            "tokens": [
                "<step>",
                "F",
                "</step>",
                "<octave>",
                "5",
                "</octave>",
                "<duration>",
                "2",
                "</duration>",
                "<step>",
                "G",
                "</step>",
                "<octave>",
                "5",
                "</octave>",
            ],
            "token_text": "F5 G5",
            "warnings": [],
        },
    )

    result = pipeline.generate("Create an 8 bar calm piano sketch in C major.")

    assert result["metadata"]["generator_mode"] == "model_conditioned"
    assert result["metadata"]["symbolic_model"]["loaded"] is True
    assert result["metadata"]["symbolic_model"]["name"] == "unit_test_model"
    assert result["generation"]["conditioning"]["degree_hints"][:2] == ["4", "5"]
    assert "Model-conditioned motif" in result["plan"]["measures"][0]["description"]
    assert result["validation"]["valid"] is True

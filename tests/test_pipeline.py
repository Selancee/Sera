from pathlib import Path

from backend.pipeline import SeraPipeline


def test_generate_creates_valid_artifacts(tmp_path: Path) -> None:
    pipeline = SeraPipeline(tmp_path)
    result = pipeline.generate("Create an 8 bar calm piano sketch in C major at 96 bpm.")

    assert result["validation"]["valid"] is True
    assert result["evaluation"]["bar_completeness"] == 1.0
    assert len(result["plan"]["measures"]) == 8
    assert Path(result["artifacts"]["musicxml_path"]).exists()
    assert Path(result["artifacts"]["midi_path"]).exists()
    assert Path(result["artifacts"]["abc_path"]).exists()
    assert Path(result["artifacts"]["pdf_path"]).exists()
    assert (tmp_path / "data" / "metadata" / "experiment_logs.jsonl").exists()


def test_revision_persists_new_run(tmp_path: Path) -> None:
    pipeline = SeraPipeline(tmp_path)
    first = pipeline.generate("Create an 8 bar piano sketch.")
    revised = pipeline.revise(first["run_id"], "Make it simpler.")

    assert revised["run_id"] != first["run_id"]
    assert "Revision feedback" in revised["prompt"]
    assert revised["validation"]["valid"] is True


def test_human_rating_updates_experiment_record(tmp_path: Path) -> None:
    pipeline = SeraPipeline(tmp_path)
    result = pipeline.generate("Create an 8 measure piano sketch.")
    rated = pipeline.rate_run(
        result["run_id"],
        {
            "prompt_adherence": 5,
            "musical_coherence": 4,
            "notation_readability": 5,
            "playability": 4,
            "editability": 5,
            "preference": "revised",
            "notes": "Clear enough for a paper demo.",
        },
    )

    assert rated["user_rating"]["average_score"] == 4.6
    assert Path(rated["metadata"]["human_rating_path"]).exists()
    assert pipeline.logger.get_record(result["run_id"])["user_rating"]["prompt_adherence"] == 5
    assert len(pipeline.logger.list_records()) == 1

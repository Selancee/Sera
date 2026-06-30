from pathlib import Path

from backend.pipeline import SeraPipeline


def test_hybrid_v05_generation_falls_back_without_checkpoint(tmp_path: Path) -> None:
    pipeline = SeraPipeline(tmp_path)
    result = pipeline.generate("Create an 8 bar calm piano sketch in C major.", generator_mode="hybrid_v05")

    assert result["validation"]["valid"] is True
    assert result["metadata"]["generator_mode"] == "hybrid_v05"
    assert "postprocess_report" in result["metadata"]
    assert result["evaluation"]["overall_musicality_proxy_score"] >= 0.0

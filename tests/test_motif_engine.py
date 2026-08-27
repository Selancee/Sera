from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.motif_engine import MotifEngine


def test_motif_engine_creates_seed_recurrence_and_cadence_resolution() -> None:
    plan = MotifEngine().generate(GenerationProfile(), 8)
    strategies = [measure["strategy"] for measure in plan["measures"]]
    assert plan["seed_motif"]
    assert "repeat" in strategies
    assert "cadence_resolution" in strategies
    assert any(measure["section"] == "B" for measure in plan["measures"])

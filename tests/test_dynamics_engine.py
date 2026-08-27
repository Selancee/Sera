from backend.generation.musicality.dynamics_engine import DynamicsEngine
from backend.generation.musicality.generation_profile import GenerationProfile


def test_dynamics_engine_adds_phrase_level_contrast() -> None:
    plan = DynamicsEngine().generate(GenerationProfile(cadence_strength="strong"), 8)
    dynamics = [measure["dynamic"] for measure in plan["measures"]]
    expressions = [measure["expression"] for measure in plan["measures"]]
    assert "f" in dynamics
    assert "crescendo" in expressions
    assert expressions[-1] == "cadence emphasis"

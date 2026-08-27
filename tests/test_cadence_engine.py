from backend.generation.musicality.cadence_engine import CadenceEngine
from backend.generation.musicality.generation_profile import GenerationProfile


def test_cadence_engine_places_phrase_and_final_cadences() -> None:
    plan = CadenceEngine().generate(GenerationProfile(cadence_strength="strong"), 8)
    cadences = {item["measure"]: item["cadence"] for item in plan["measures"]}
    assert cadences[4] == "half"
    assert cadences[8] == "authentic"
    assert plan["final_cadence"] == "authentic"

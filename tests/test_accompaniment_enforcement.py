from backend.pipeline import SeraPipeline


def test_intermediate_piano_has_left_hand_in_most_measures(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate("Compose an 8 measure intermediate cyberpunk piano passage.", generator_mode="rule_based")
    measures = result["score_document"]["measures"]
    active_left = [
        measure
        for measure in measures
        if any(event.get("staff") == "left_hand" and event.get("type") != "rest" for event in measure.get("events", []))
    ]

    assert len(active_left) / len(measures) >= 0.7

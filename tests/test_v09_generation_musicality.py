from pathlib import Path

from backend.pipeline import SeraPipeline


def test_v09_rule_based_generation_has_rhythm_cadence_and_left_hand(tmp_path: Path) -> None:
    pipeline = SeraPipeline(tmp_path)
    result = pipeline.generate(
        "Compose an 8 bar romantic piano piece with dotted rhythm and flowing left hand.",
        generator_mode="rule_based",
        musicality_controls={"rhythmic_density": "high", "texture": "arpeggiated", "accompaniment_style": "arpeggiated_chords"},
    )

    events = [event for measure in result["score_document"]["measures"] for event in measure["events"]]
    durations = {event["duration"] for event in events}
    assert result["validation"]["valid"] is True
    assert any(duration in durations for duration in {"eighth", "sixteenth", "dotted_quarter", "dotted_eighth"})
    assert durations != {"quarter"}
    assert any(event["staff"] == "left_hand" for event in events)
    assert result["metadata"]["cadence_plan"]["final_cadence"] in {"authentic", "modal_pentatonic_ending"}
    assert result["metadata"]["generation_profile"]["requires_accompaniment"] is True
    assert result["evaluation"]["rhythmic_diversity_score"] > 0

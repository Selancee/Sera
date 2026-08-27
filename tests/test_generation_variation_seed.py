from backend.generation.rule_based_generator import RuleBasedGenerator
from backend.models.schemas import CompositionPlan, MeasurePlan, StructuredMusicIntent


def _plan(seed: str) -> CompositionPlan:
    intent = StructuredMusicIntent(
        prompt="Compose a romantic piano passage with flowing left hand.",
        style="romantic",
        key="A minor",
        time_signature="4/4",
        bars=8,
        instruments=["piano"],
        texture="melody_accompaniment",
        rhythmic_density="medium",
    )
    intent.constraints.append(f"variation_seed:{seed}")
    measures = [
        MeasurePlan(index=index, section="A", chord="i", function="tonic", rhythm="", density="medium")
        for index in range(1, 9)
    ]
    return CompositionPlan(intent=intent, measures=measures, global_plan={})


def test_variation_seed_changes_generated_music_but_remains_reproducible() -> None:
    generator = RuleBasedGenerator()

    first = generator.generate(_plan("seed-a"))
    first_again = generator.generate(_plan("seed-a"))
    second = generator.generate(_plan("seed-b"))

    assert first.musicxml == first_again.musicxml
    assert first.metadata["generation_profile"]["variation_seed"] == "seed-a"
    assert second.metadata["generation_profile"]["variation_seed"] == "seed-b"
    assert first.metadata["rhythm_patterns"]["measures"] != second.metadata["rhythm_patterns"]["measures"]
    assert first.metadata["motifs"]["seed_motif"] != second.metadata["motifs"]["seed_motif"]
    assert first.metadata["harmony_plan"]["progression"] != second.metadata["harmony_plan"]["progression"]
    assert first.musicxml != second.musicxml

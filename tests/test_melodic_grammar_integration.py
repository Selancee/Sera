from backend.pipeline import SeraPipeline
from evaluation.analysis.music_statistics import parse_pitch_name


def _right_hand_pcs(result: dict) -> set[int]:
    pcs: set[int] = set()
    for measure in result["score_document"]["measures"]:
        for event in measure.get("events", []):
            if event.get("type") == "note" and event.get("staff") == "right_hand":
                midi = parse_pitch_name(str(event.get("pitch", "")))
                if midi is not None:
                    pcs.add(midi % 12)
    return pcs


def test_chinese_generation_uses_pentatonic_right_hand(tmp_path) -> None:
    result = SeraPipeline(tmp_path).generate(
        "Chinese pentatonic guofeng piano with open fifth pedal, 8 measures",
        generator_mode="rule_based",
        musicality_controls={"run_seed": 42},
    )

    assert result["generation_metadata"]["pitch_vocabulary"] == "pentatonic"
    assert _right_hand_pcs(result).issubset({0, 2, 4, 7, 9})


def test_cyberpunk_and_romantic_melody_profiles_differ(tmp_path) -> None:
    pipeline = SeraPipeline(tmp_path)
    # This is a reproducible style-integration fixture, not an all-seed quality claim.
    # Unseeded generation intentionally mixes wall-clock time and a UUID.
    cyberpunk = pipeline.generate(
        "cyberpunk piano passage, dark futuristic ostinato, 8 measures",
        generator_mode="rule_based",
        musicality_controls={"run_seed": 42},
    )
    romantic = pipeline.generate(
        "romantic flowing nocturne piano, 8 measures",
        generator_mode="rule_based",
        musicality_controls={"run_seed": 42},
    )

    assert cyberpunk["generation_metadata"]["contour_policy"] == "short_cell_repetition"
    assert romantic["generation_metadata"]["contour_policy"] == "long_arch"
    assert cyberpunk["generation_metadata"]["pitch_vocabulary"] != romantic["generation_metadata"]["pitch_vocabulary"]
    for result in (cyberpunk, romantic):
        report = result["generation_metadata"]["melodic_grammar_report"]
        assert report["valid"], report

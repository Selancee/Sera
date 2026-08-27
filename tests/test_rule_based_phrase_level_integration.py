from __future__ import annotations

from pathlib import Path

from backend.pipeline import SeraPipeline
from evaluation.analysis.music_statistics import parse_pitch_name


def test_rule_based_generator_final_score_uses_phrase_melody_engine(tmp_path: Path) -> None:
    result = SeraPipeline(tmp_path / "v0962_rule_based").generate(
        "Pop piano hook, bright, repeated hook with variation, 8 measures",
        generator_mode="rule_based",
        musicality_controls={"variation_seed": "v0962-rule-based"},
        candidate_count=3,
    )
    metadata = result["generation_metadata"]
    right_hand_midis = _right_hand_midis(result["score_document"])
    phrase_midis = [midi for measure in metadata["phrase_melody"]["measures"] for midi in measure["midis"]]

    assert metadata["melody_generation_source"] == "phrase_melody_engine"
    assert metadata["hardcoded_shape_fallback_used"] is False
    assert right_hand_midis == phrase_midis
    assert max(right_hand_midis) - min(right_hand_midis) >= 7
    assert "phrase_contour_score" in metadata["candidate_generation"]["selected_candidate_metrics"]


def _right_hand_midis(score_document: dict) -> list[int]:
    midis = []
    for measure in score_document.get("measures", []):
        for event in measure.get("events", []):
            if event.get("staff") != "right_hand" or event.get("type") == "rest" or not event.get("pitch"):
                continue
            midi = parse_pitch_name(str(event["pitch"]))
            if midi is not None:
                midis.append(int(midi))
    return midis

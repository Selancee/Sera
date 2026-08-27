from __future__ import annotations

from pathlib import Path

from backend.pipeline import SeraPipeline
from evaluation.analysis.music_statistics import parse_pitch_name


def test_v0962_final_score_contains_phrase_reports_and_measure_metadata(tmp_path: Path) -> None:
    result = SeraPipeline(tmp_path / "v0962_final_score").generate(
        "Classical piano period, antecedent and consequent, clear cadence, 8 measures",
        generator_mode="rule_based",
        musicality_controls={"variation_seed": "v0962-final-score"},
        candidate_count=3,
    )
    metadata = result["generation_metadata"]
    score = result["score_document"]

    assert metadata["phrase_melody"]["engine"] == "phrase_melody_engine_v0962"
    assert metadata["motif_memory_report"]["motif_recurrence_count"] >= 2
    assert metadata["target_tone_report"]["target_tone_hit_rate"] > 0.0
    assert metadata["tension_release_report"]["curve_match_score"] > 0.0
    assert score["measures"][0]["metadata"]["phrase_melody"]["phrase_id"]
    assert _measure_pitch_fingerprints(score)[0] != _measure_pitch_fingerprints(score)[1]


def _measure_pitch_fingerprints(score_document: dict) -> list[tuple[int, ...]]:
    fingerprints = []
    for measure in score_document.get("measures", []):
        pitches = []
        for event in measure.get("events", []):
            if event.get("staff") != "right_hand" or event.get("type") == "rest":
                continue
            midi = parse_pitch_name(str(event.get("pitch", "")))
            if midi is not None:
                pitches.append(int(midi))
        fingerprints.append(tuple(pitches))
    return fingerprints

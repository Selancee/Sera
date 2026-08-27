from __future__ import annotations

from pathlib import Path

from backend.generation.musicality.melodic_style_engine import build_melodic_style_profile
from backend.pipeline import SeraPipeline
from evaluation.analysis.music_statistics import parse_pitch_name


def _generate(tmp_path: Path, prompt: str, seed: str = "v0961-test") -> dict:
    return SeraPipeline(tmp_path / seed.replace(" ", "_")).generate(
        prompt,
        generator_mode="rule_based",
        musicality_controls={"variation_seed": seed},
        candidate_count=4,
    )


def test_v0961_melodic_style_families_are_not_default() -> None:
    jazz = build_melodic_style_profile({"base_style": "jazz"}, "F major", "major", "advanced")
    pop = build_melodic_style_profile({"base_style": "pop"}, "C major", "major", "intermediate")
    classical = build_melodic_style_profile({"base_style": "classical"}, "C major", "major", "intermediate")

    assert jazz["style_family"] == "jazz"
    assert pop["style_family"] == "pop"
    assert classical["style_family"] == "classical"
    assert jazz["pitch_vocabulary"] != "diatonic"
    assert pop["contour_policy"] == "hook_based_repetition_with_variation"


def test_v0961_jazz_final_score_uses_expectation_harmony_and_actual_voicing(tmp_path: Path) -> None:
    result = _generate(tmp_path, "Jazz piano sketch, ii-V-I, seventh chords, 8 measures", "v0961-jazz")
    metadata = result["generation_metadata"]
    actual = metadata["actual_harmony_style_report"]
    harmony = metadata["harmony_plan"]

    assert metadata["melody_generation_source"] == "phrase_melody_engine"
    assert metadata["hardcoded_shape_fallback_used"] is False
    assert metadata["melodic_style_profile"]["style_family"] == "jazz"
    assert any("7" in chord or "maj9" in chord or "alt" in chord for chord in harmony["chords"])
    assert harmony["old_variation_override_used"] is False
    assert actual["style"] == "jazz"
    assert actual["contains_sevenths"] is True
    assert actual["contains_extensions"] is True
    assert actual["plain_triad_only"] is False
    assert actual["style_harmony_match_score"] >= 0.8


def test_v0961_pop_and_classical_final_styles_are_realized(tmp_path: Path) -> None:
    pop = _generate(tmp_path, "Pop piano hook, bright, I-V-vi-IV, 8 measures", "v0961-pop")
    classical = _generate(tmp_path, "Classical piano period, clear cadence, 8 measures", "v0961-classical")

    pop_meta = pop["generation_metadata"]
    classical_meta = classical["generation_metadata"]
    assert pop_meta["melodic_style_profile"]["style_family"] == "pop"
    assert pop_meta["harmony_plan"]["progression"] in [["I", "V", "vi", "IV"], ["vi", "IV", "I", "V"], ["I", "vi", "IV", "V"]]
    assert pop_meta["actual_harmony_style_report"]["style_harmony_match_score"] >= 0.7
    assert classical_meta["melodic_style_profile"]["style_family"] == "classical"
    assert "V7" in classical_meta["harmony_plan"]["chords"]
    assert classical_meta["actual_harmony_style_report"]["style_harmony_match_score"] >= 0.75


def test_v0961_chinese_and_cyberpunk_actual_score_traits(tmp_path: Path) -> None:
    chinese = _generate(tmp_path, "Chinese pentatonic piano in D major, open fifths, 8 measures", "v0961-chinese")
    cyberpunk = _generate(tmp_path, "Cyberpunk piano, ostinato bass, minor modal, syncopation, 8 measures", "v0961-cyberpunk")

    chinese_meta = chinese["generation_metadata"]
    chinese_actual = chinese_meta["actual_harmony_style_report"]
    assert chinese_meta["melodic_style_profile"]["style_family"] == "chinese"
    assert chinese_actual["contains_open_fifths"] is True
    assert _pentatonic_rate(chinese["score_document"], "D major") >= 0.75

    cyber_actual = cyberpunk["generation_metadata"]["actual_harmony_style_report"]
    assert cyberpunk["generation_metadata"]["melodic_style_profile"]["style_family"] == "cyberpunk"
    assert cyber_actual["contains_ostinato"] is True
    assert cyber_actual["contains_pedal_point"] is True


def test_v0961_candidate_generation_has_actual_music_diversity(tmp_path: Path) -> None:
    result = _generate(tmp_path, "Jazz piano sketch, ii-V-I, seventh chords, 8 measures", "v0961-diversity")
    diversity = result["generation_metadata"]["candidate_generation"]["candidate_actual_diversity"]

    assert diversity["melody_distinct_count"] >= 2
    assert diversity["rhythm_distinct_count"] >= 2
    assert diversity["harmony_distinct_count"] >= 2


def _pentatonic_rate(score_document: dict, key: str) -> float:
    tonic = _tonic_pc(key)
    allowed = {(tonic + interval) % 12 for interval in (0, 2, 4, 7, 9)}
    pcs = []
    for measure in score_document.get("measures", []):
        for event in measure.get("events", []):
            if event.get("staff") != "right_hand" or event.get("type") == "rest" or not event.get("pitch"):
                continue
            midi = parse_pitch_name(str(event.get("pitch")))
            if midi is not None:
                pcs.append(midi % 12)
    return sum(1 for pc in pcs if pc in allowed) / max(1, len(pcs))


def _tonic_pc(key: str) -> int:
    token = key.split()[0]
    step = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}.get(token[0].upper(), 0)
    if len(token) > 1 and token[1] == "#":
        step += 1
    if len(token) > 1 and token[1] == "b":
        step -= 1
    return step % 12

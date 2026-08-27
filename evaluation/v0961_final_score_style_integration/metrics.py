"""Final ScoreDocument metrics for V0.96.1 style integration."""

from __future__ import annotations

from typing import Any

from evaluation.analysis.music_statistics import parse_pitch_name


def final_score_style_metrics(result: dict[str, Any], expected_family: str = "") -> dict[str, float]:
    metadata = dict(result.get("generation_metadata") or {})
    family = str((metadata.get("melodic_style_profile") or {}).get("style_family", ""))
    actual = dict(metadata.get("actual_harmony_style_report") or {})
    expectation = dict(metadata.get("melody_expectation_report") or {})
    return {
        "final_melody_style_match_rate": 1.0 if family == expected_family else 0.0,
        "final_harmony_style_match_rate": float(actual.get("style_harmony_match_score", 0.0) or 0.0),
        "actual_voicing_style_match_rate": 0.0 if actual.get("plain_triad_only") and actual.get("style") == "jazz" else float(actual.get("style_harmony_match_score", 0.0) or 0.0),
        "metadata_score_consistency_rate": _metadata_consistency(metadata),
        "melody_expectation_score": float(expectation.get("melody_expectation_score", 0.0) or 0.0),
    }


def style_specific_metrics(result: dict[str, Any]) -> dict[str, float]:
    metadata = dict(result.get("generation_metadata") or {})
    actual = dict(metadata.get("actual_harmony_style_report") or {})
    score_document = dict(result.get("score_document") or {})
    family = str((metadata.get("melodic_style_profile") or {}).get("style_family", ""))
    return {
        "jazz_actual_extension_presence_rate": 1.0 if actual.get("style") == "jazz" and (actual.get("contains_sevenths") or actual.get("contains_extensions")) else 0.0,
        "jazz_plain_triad_failure_rate": 1.0 if actual.get("style") == "jazz" and actual.get("plain_triad_only") else 0.0,
        "pop_hook_contour_score": _hook_score(score_document) if family == "pop" else 1.0,
        "classical_leading_tone_resolution_rate": 1.0 if family != "classical" or "V7" in " ".join(str(item) for item in (metadata.get("harmony_plan") or {}).get("chords", [])) else 0.0,
        "chinese_pentatonic_actual_note_rate": _pentatonic_rate(score_document, "D major") if family == "chinese" else 1.0,
        "cyberpunk_ostinato_actual_rate": 1.0 if family != "cyberpunk" or actual.get("contains_ostinato") else 0.0,
        "romantic_long_line_actual_score": _line_range_score(score_document) if family == "romantic" else 1.0,
    }


def candidate_diversity_metrics(result: dict[str, Any]) -> dict[str, float]:
    diversity = dict(((result.get("generation_metadata") or {}).get("candidate_generation") or {}).get("candidate_actual_diversity") or {})
    return {
        "candidate_actual_melody_diversity_score": float(diversity.get("melody_diversity_score", 0.0) or 0.0),
        "candidate_actual_harmony_diversity_score": float(diversity.get("harmony_diversity_score", 0.0) or 0.0),
        "candidate_actual_rhythm_diversity_score": float(diversity.get("rhythm_diversity_score", 0.0) or 0.0),
    }


def pass_score(row: dict[str, Any]) -> float:
    checks = [
        float(row.get("final_melody_style_match_rate", 1.0) or 0.0) >= 1.0,
        float(row.get("final_harmony_style_match_rate", 1.0) or 0.0) >= 0.65,
        float(row.get("actual_voicing_style_match_rate", 1.0) or 0.0) >= 0.65,
        float(row.get("jazz_plain_triad_failure_rate", 0.0) or 0.0) == 0.0,
        float(row.get("candidate_actual_melody_diversity_score", 1.0) or 0.0) >= 0.5,
    ]
    return 1.0 if all(checks) else 0.0


def _metadata_consistency(metadata: dict[str, Any]) -> float:
    actual = dict(metadata.get("actual_harmony_style_report") or {})
    metadata_score = float(metadata.get("harmony_style_score", actual.get("style_harmony_match_score", 0.0)) or 0.0)
    actual_score = float(actual.get("style_harmony_match_score", 0.0) or 0.0)
    melody_source_ok = metadata.get("melody_generation_source") in {"expectation_engine", "phrase_melody_engine"}
    return 1.0 if abs(metadata_score - actual_score) <= 0.25 and melody_source_ok else 0.0


def _hook_score(score_document: dict[str, Any]) -> float:
    pcs = _right_hand_pcs(score_document)
    if len(pcs) < 4:
        return 0.0
    repeated = len(pcs) - len(set(pcs))
    range_ok = max(pcs) - min(pcs) <= 11 if pcs else False
    return min(1.0, repeated / max(1, len(pcs) - 1) + (0.35 if range_ok else 0.0))


def _line_range_score(score_document: dict[str, Any]) -> float:
    midis = _right_hand_midis(score_document)
    if len(midis) < 4:
        return 0.0
    return min(1.0, (max(midis) - min(midis)) / 14)


def _pentatonic_rate(score_document: dict[str, Any], key: str) -> float:
    tonic = _tonic_pc(key)
    allowed = {(tonic + interval) % 12 for interval in (0, 2, 4, 7, 9)}
    pcs = _right_hand_pcs(score_document)
    return sum(1 for pc in pcs if pc in allowed) / max(1, len(pcs))


def _right_hand_pcs(score_document: dict[str, Any]) -> list[int]:
    return [midi % 12 for midi in _right_hand_midis(score_document)]


def _right_hand_midis(score_document: dict[str, Any]) -> list[int]:
    midis = []
    for measure in score_document.get("measures", []):
        for event in measure.get("events", []):
            if event.get("staff") != "right_hand" or event.get("type") == "rest" or not event.get("pitch"):
                continue
            midi = parse_pitch_name(str(event.get("pitch")))
            if midi is not None:
                midis.append(int(midi))
    return midis


def _tonic_pc(key: str) -> int:
    token = key.split()[0]
    step = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}.get(token[0].upper(), 0)
    if len(token) > 1 and token[1] == "#":
        step += 1
    if len(token) > 1 and token[1] == "b":
        step -= 1
    return step % 12

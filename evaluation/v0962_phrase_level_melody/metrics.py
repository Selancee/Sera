"""Final ScoreDocument metrics for V0.96.2 phrase melody evaluation."""

from __future__ import annotations

import copy
from statistics import mean
from typing import Any

from evaluation.analysis.music_statistics import parse_pitch_name


STABLE_MAJOR = {0, 4, 7}
STABLE_MINOR = {0, 3, 7}
PENTATONIC = {0, 2, 4, 7, 9}
MINOR_MODAL = {0, 2, 3, 5, 7, 8, 10}


def phrase_melody_metrics(result: dict[str, Any], expected_style: str = "") -> dict[str, Any]:
    """Compute phrase-level metrics from the final ScoreDocument."""

    score = dict(result.get("score_document") or {})
    metadata = dict(result.get("generation_metadata") or {})
    midis_by_measure = _right_hand_midis_by_measure(score)
    midis = [midi for measure in midis_by_measure for midi in measure]
    metadata_scores = dict((metadata.get("phrase_melody") or {}).get("phrase_level_scores") or {})
    metrics = {
        "melody_generation_source": metadata.get("melody_generation_source", ""),
        "hardcoded_shape_fallback_used": bool(metadata.get("hardcoded_shape_fallback_used", True)),
        "phrase_contour_score": _phrase_contour_score(midis_by_measure),
        "motif_development_score": _motif_development_score(midis_by_measure),
        "mechanical_repetition_penalty": _mechanical_repetition_penalty(midis_by_measure),
        "target_tone_hit_rate": _stable_target_hit_rate(score),
        "tension_release_curve_match_score": float(metadata_scores.get("tension_release_score", 0.0) or 0.0),
        "cadence_preparation_score": _cadence_preparation_score(score),
        "accompaniment_interaction_score": 0.75 if (metadata.get("accompaniment_interaction_report") or {}).get("melody_supported") else 0.0,
        "style_phrase_match_score": _style_phrase_score(score, expected_style),
        "melody_expectation_score": float((metadata.get("melody_expectation_report") or {}).get("melody_expectation_score", 0.0) or 0.0),
        "final_melody_range": max(midis) - min(midis) if midis else 0,
        "final_melody_fingerprint": _fingerprint(midis_by_measure),
    }
    metrics["final_score_musicality_proxy"] = round(
        mean(
            [
                float(metrics["phrase_contour_score"]),
                float(metrics["motif_development_score"]),
                float(metrics["target_tone_hit_rate"]),
                float(metrics["cadence_preparation_score"]),
                float(metrics["style_phrase_match_score"]),
                max(0.0, 1.0 - float(metrics["mechanical_repetition_penalty"])),
            ]
        ),
        4,
    )
    return metrics


def baseline_template_metrics(result: dict[str, Any], expected_style: str = "") -> dict[str, Any]:
    """Simulate the old repeated-measure template path on the final score rhythm."""

    baseline = simulate_template_baseline(dict(result.get("score_document") or {}))
    metrics = phrase_melody_metrics({"score_document": baseline, "generation_metadata": {}}, expected_style)
    metrics["melody_generation_source"] = "simulated_v0961_template_baseline"
    return metrics


def simulate_template_baseline(score_document: dict[str, Any]) -> dict[str, Any]:
    """Replace right-hand pitches with the old repeated C-D-E-F-C style cell."""

    score = copy.deepcopy(score_document or {})
    template = ["C4", "D4", "E4", "F4", "C4"]
    for measure in score.get("measures", []):
        index = 0
        for event in measure.get("events", []):
            if event.get("staff") != "right_hand" or event.get("type") == "rest":
                continue
            event["pitch"] = template[index % len(template)]
            index += 1
    return score


def pass_score(row: dict[str, Any]) -> float:
    checks = [
        row.get("melody_generation_source") == "phrase_melody_engine",
        not bool(row.get("hardcoded_shape_fallback_used", True)),
        float(row.get("final_score_musicality_proxy", 0.0) or 0.0) >= 0.55,
        float(row.get("mechanical_repetition_penalty", 1.0) or 0.0) <= 0.35,
        float(row.get("final_melody_range", 0.0) or 0.0) >= 7,
    ]
    return 1.0 if all(checks) else 0.0


def _right_hand_midis_by_measure(score_document: dict[str, Any]) -> list[list[int]]:
    out = []
    for measure in score_document.get("measures", []):
        midis = []
        for event in measure.get("events", []):
            if event.get("staff") != "right_hand" or event.get("type") == "rest" or not event.get("pitch"):
                continue
            midi = parse_pitch_name(str(event.get("pitch")))
            if midi is not None:
                midis.append(int(midi))
        out.append(midis)
    return out


def _phrase_contour_score(midis_by_measure: list[list[int]]) -> float:
    averages = [mean(values) for values in midis_by_measure if values]
    if len(averages) < 3:
        return 0.0
    changes = [averages[index + 1] - averages[index] for index in range(len(averages) - 1)]
    non_flat = sum(1 for value in changes if abs(value) >= 1.0)
    has_release = averages[-1] <= max(averages) + 0.1
    return round(min(1.0, non_flat / max(1, len(changes)) + (0.2 if has_release else 0.0)), 4)


def _motif_development_score(midis_by_measure: list[list[int]]) -> float:
    fingerprints = [_interval_fingerprint(measure) for measure in midis_by_measure if len(measure) >= 3]
    if len(fingerprints) < 2:
        return 0.0
    exact = len(fingerprints) - len(set(fingerprints))
    related = 0
    first = fingerprints[0].split(",")
    for fingerprint in fingerprints[1:]:
        parts = fingerprint.split(",")
        span = min(len(first), len(parts))
        if span and sum(1 for a, b in zip(first, parts, strict=False) if a == b) / span >= 0.4:
            related += 1
    return round(min(1.0, (related + 0.5 * exact) / max(1, len(fingerprints) - 1)), 4)


def _mechanical_repetition_penalty(midis_by_measure: list[list[int]]) -> float:
    fingerprints = [_interval_fingerprint(measure) for measure in midis_by_measure if measure]
    if not fingerprints:
        return 1.0
    exact = len(fingerprints) - len(set(fingerprints))
    return round(exact / max(1, len(fingerprints)), 4)


def _stable_target_hit_rate(score_document: dict[str, Any]) -> float:
    key = str(score_document.get("global", {}).get("key", "C major"))
    stable = _stable_pcs(key)
    checks = []
    for measure in score_document.get("measures", []):
        right = []
        for event in measure.get("events", []):
            if event.get("staff") != "right_hand" or event.get("type") == "rest":
                continue
            midi = parse_pitch_name(str(event.get("pitch", "")))
            if midi is not None:
                right.append((float(event.get("offset", 0.0) or 0.0), int(midi)))
        if not right:
            continue
        for offset, midi in right:
            if abs(offset - round(offset)) < 0.01:
                checks.append(midi % 12 in stable)
        checks.append(right[-1][1] % 12 in stable)
    return round(sum(1 for item in checks if item) / max(1, len(checks)), 4)


def _cadence_preparation_score(score_document: dict[str, Any]) -> float:
    key = str(score_document.get("global", {}).get("key", "C major"))
    stable = _stable_pcs(key)
    last_measure = (score_document.get("measures") or [{}])[-1]
    right = []
    for event in last_measure.get("events", []):
        if event.get("staff") != "right_hand" or event.get("type") == "rest":
            continue
        midi = parse_pitch_name(str(event.get("pitch", "")))
        if midi is not None:
            right.append((int(midi), str(event.get("duration", ""))))
    if not right:
        return 0.0
    stable_end = 1.0 if right[-1][0] % 12 in stable else 0.25
    settled_duration = 1.0 if right[-1][1] in {"quarter", "half", "dotted_quarter", "whole"} else 0.55
    return round(mean([stable_end, settled_duration]), 4)


def _style_phrase_score(score_document: dict[str, Any], expected_style: str) -> float:
    key = str(score_document.get("global", {}).get("key", "C major"))
    tonic = _tonic_pc(key)
    midis = [midi for measure in _right_hand_midis_by_measure(score_document) for midi in measure]
    if not midis:
        return 0.0
    pcs = [midi % 12 for midi in midis]
    if expected_style == "chinese":
        allowed = {(tonic + pc) % 12 for pc in PENTATONIC}
        return round(sum(1 for pc in pcs if pc in allowed) / len(pcs), 4)
    if expected_style == "cyberpunk":
        allowed = {(tonic + pc) % 12 for pc in MINOR_MODAL}
        return round(sum(1 for pc in pcs if pc in allowed) / len(pcs), 4)
    if expected_style == "pop":
        return round(min(1.0, 0.35 + _motif_development_score(_right_hand_midis_by_measure(score_document))), 4)
    if expected_style == "romantic":
        return round(min(1.0, (max(midis) - min(midis)) / 14), 4)
    return round(_stable_target_hit_rate(score_document), 4)


def _interval_fingerprint(midis: list[int]) -> str:
    if len(midis) < 2:
        return ""
    return ",".join(str(max(-7, min(7, midis[index + 1] - midis[index]))) for index in range(len(midis) - 1))


def _fingerprint(midis_by_measure: list[list[int]]) -> str:
    return "|".join(_interval_fingerprint(measure) for measure in midis_by_measure)


def _stable_pcs(key: str) -> set[int]:
    tonic = _tonic_pc(key)
    base = STABLE_MINOR if "minor" in key.lower() else STABLE_MAJOR
    return {(tonic + pc) % 12 for pc in base}


def _tonic_pc(key: str) -> int:
    token = str(key or "C").split()[0].replace("-flat", "b")
    if not token:
        return 0
    step = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}.get(token[0].upper(), 0)
    if len(token) > 1 and token[1] == "#":
        step += 1
    if len(token) > 1 and token[1].lower() == "b":
        step -= 1
    return step % 12

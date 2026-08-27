"""Deterministic texture recognition over a bounded canonical ScoreDocument scope."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from itertools import combinations
from statistics import mean
from typing import Any

from backend.services.score_document_service import normalize_score_document
from evaluation.analysis.music_statistics import parse_pitch_name
from sera_edit.domain.score_scope import EventContext, ScoreScope


TEXTURE_LABELS = {
    "unknown",
    "monophonic",
    "homorhythmic_chordal",
    "melody_accompaniment",
    "contrapuntal",
    "layered",
}


def analyze_texture(score_document: dict[str, Any], target_scope: dict[str, Any]) -> dict[str, Any]:
    """Describe attack alignment, voice independence, register, and likely texture.

    This is deliberately an auditable symbolic heuristic, not an audio classifier.
    It never changes the score and does not claim that one texture label remains
    valid for the whole work.
    """

    score = normalize_score_document(score_document)
    scope = ScoreScope.from_dict(target_scope)
    notes = [context for context in scope.select(score) if context.event.get("type") == "note"]
    groups: dict[str, list[EventContext]] = defaultdict(list)
    for context in notes:
        groups[_voice_id(context)].append(context)
    for contexts in groups.values():
        contexts.sort(key=lambda item: (item.measure, item.offset, item.event_id))

    voice_roles = _voice_roles(score)
    voice_rows: list[dict[str, Any]] = []
    onset_sets: dict[str, set[tuple[int, str]]] = {}
    for voice_id, contexts in sorted(groups.items()):
        onsets = {(item.measure, str(item.offset)) for item in contexts}
        onset_sets[voice_id] = onsets
        midis = [parse_pitch_name(str(item.event.get("pitch", ""))) for item in contexts]
        valid_midis = [int(value) for value in midis if value is not None]
        voice_rows.append(
            {
                "voice_id": voice_id,
                "staff": contexts[0].staff,
                "voice": contexts[0].voice,
                "role": voice_roles.get(voice_id, "unassigned"),
                "note_count": len(contexts),
                "unique_onset_count": len(onsets),
                "mean_pitch": round(mean(valid_midis), 4) if valid_midis else None,
                "pitch_range": [min(valid_midis), max(valid_midis)] if valid_midis else None,
            }
        )

    distinct_onsets = sorted({onset for values in onset_sets.values() for onset in values})
    simultaneous_onsets = sum(
        sum(onset in values for values in onset_sets.values()) >= 2 for onset in distinct_onsets
    )
    attack_alignment_ratio = simultaneous_onsets / max(1, len(distinct_onsets))
    pairwise_jaccard = [
        len(onset_sets[left] & onset_sets[right]) / max(1, len(onset_sets[left] | onset_sets[right]))
        for left, right in combinations(sorted(onset_sets), 2)
    ]
    homorhythmic_similarity = mean(pairwise_jaccard) if pairwise_jaccard else 1.0
    rhythmic_independence = 0.0 if len(groups) <= 1 else 1.0 - homorhythmic_similarity
    primary_voice_id = _primary_voice(voice_rows)
    support_rows = [row for row in voice_rows if row["voice_id"] != primary_voice_id]
    primary_row = next((row for row in voice_rows if row["voice_id"] == primary_voice_id), None)
    support_pitches = [float(row["mean_pitch"]) for row in support_rows if row["mean_pitch"] is not None]
    register_separation = (
        abs(float(primary_row["mean_pitch"]) - mean(support_pitches))
        if primary_row and primary_row["mean_pitch"] is not None and support_pitches
        else 0.0
    )
    measures = sorted({context.measure for context in notes})
    notes_per_measure = len(notes) / max(1, len(measures))
    label, confidence, evidence = _classify(
        voice_count=len(groups),
        attack_alignment_ratio=attack_alignment_ratio,
        homorhythmic_similarity=homorhythmic_similarity,
        rhythmic_independence=rhythmic_independence,
        register_separation=register_separation,
        primary_role=str((primary_row or {}).get("role") or ""),
        notes_per_measure=notes_per_measure,
    )
    payload = {
        "analysis_version": "0.4.0",
        "classifier": "sera_symbolic_texture_heuristic_v1",
        "texture": label,
        "confidence": round(confidence, 4),
        "evidence": evidence,
        "measure_count": len(measures),
        "selected_note_count": len(notes),
        "voice_count": len(groups),
        "primary_voice_id": primary_voice_id,
        "attack_alignment_ratio": round(attack_alignment_ratio, 4),
        "homorhythmic_similarity": round(homorhythmic_similarity, 4),
        "rhythmic_independence": round(rhythmic_independence, 4),
        "register_separation_semitones": round(register_separation, 4),
        "notes_per_measure": round(notes_per_measure, 4),
        "voices": voice_rows,
        "limitations": [
            "Symbolic attack-pattern heuristic; sustained overlap and timbre are not modeled.",
            "The label applies only to the selected scope and may hide local texture changes.",
        ],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["fingerprint"] = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
    return payload


def _voice_id(context: EventContext) -> str:
    return f"{context.staff}:v{context.voice}"


def _voice_roles(score: dict[str, Any]) -> dict[str, str]:
    roles: dict[str, str] = {}
    for track in score.get("tracks") or []:
        staff = str(track.get("staff") or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not staff:
            continue
        voice = int(track.get("voice", 1) or 1)
        roles[f"{staff}:v{voice}"] = str(track.get("role") or "unassigned")
    return roles


def _primary_voice(voice_rows: list[dict[str, Any]]) -> str | None:
    if not voice_rows:
        return None
    lead_roles = {"lead_melody", "melody", "main_melody", "solo"}
    explicit = [row for row in voice_rows if str(row.get("role")) in lead_roles]
    pool = explicit or voice_rows
    selected = max(
        pool,
        key=lambda row: (
            str(row.get("staff")) == "right_hand",
            int(row.get("note_count") or 0),
            float(row.get("mean_pitch") or -999),
            str(row.get("voice_id")),
        ),
    )
    return str(selected["voice_id"])


def _classify(
    *,
    voice_count: int,
    attack_alignment_ratio: float,
    homorhythmic_similarity: float,
    rhythmic_independence: float,
    register_separation: float,
    primary_role: str,
    notes_per_measure: float,
) -> tuple[str, float, list[str]]:
    if voice_count == 0:
        return "unknown", 0.0, ["no_notes_in_scope"]
    if voice_count <= 1:
        return "monophonic", 0.98, ["single_active_voice"]
    if homorhythmic_similarity >= 0.76 and attack_alignment_ratio >= 0.58:
        confidence = min(0.98, 0.55 + 0.25 * homorhythmic_similarity + 0.2 * attack_alignment_ratio)
        return "homorhythmic_chordal", confidence, ["high_onset_alignment", "similar_voice_rhythm"]
    has_explicit_melody = primary_role in {"lead_melody", "melody", "main_melody", "solo"}
    if has_explicit_melody or register_separation >= 5.0:
        confidence = min(0.95, 0.55 + 0.2 * rhythmic_independence + 0.025 * min(register_separation, 8.0))
        return "melody_accompaniment", confidence, ["primary_line_identified", "supporting_voice_contrast"]
    if voice_count >= 2 and rhythmic_independence >= 0.48:
        confidence = min(0.92, 0.5 + 0.45 * rhythmic_independence)
        return "contrapuntal", confidence, ["independent_attack_patterns", "multiple_active_voices"]
    confidence = min(0.86, 0.48 + 0.03 * min(voice_count, 6) + 0.01 * min(notes_per_measure, 12.0))
    return "layered", confidence, ["multiple_layers", "mixed_alignment"]

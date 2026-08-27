"""Deterministic phrase and motif analysis over a bounded ScoreScope."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from statistics import mean
from typing import Any

from backend.services.score_document_service import normalize_score_document
from evaluation.analysis.music_statistics import parse_pitch_name
from sera_edit.domain.score_scope import EventContext, ScoreScope


def analyze_phrase(score_document: dict[str, Any], target_scope: dict[str, Any]) -> dict[str, Any]:
    """Summarize source contour, motif identity, and register by voice."""

    score = normalize_score_document(score_document)
    scope = ScoreScope.from_dict(target_scope)
    selected = [context for context in scope.select(score) if context.event.get("type") == "note"]
    groups: dict[tuple[str, int], list[EventContext]] = defaultdict(list)
    for context in selected:
        groups[(context.staff, context.voice)].append(context)
    voice_analyses: list[dict[str, Any]] = []
    for (staff, voice), contexts in groups.items():
        contexts.sort(key=lambda item: (item.measure, item.offset, item.event_id))
        midis = [parse_pitch_name(str(item.event.get("pitch", ""))) for item in contexts]
        valid_midis = [int(midi) for midi in midis if midi is not None]
        if not valid_midis:
            continue
        intervals = [right - left for left, right in zip(valid_midis, valid_midis[1:], strict=False)]
        signature = _motif_signature(intervals)
        voice_analyses.append(
            {
                "voice_id": f"{staff}:v{voice}",
                "staff": staff,
                "voice": voice,
                "event_ids": [item.event_id for item in contexts],
                "note_count": len(valid_midis),
                "pitch_range": [min(valid_midis), max(valid_midis)],
                "mean_pitch": round(mean(valid_midis), 4),
                "intervals": intervals,
                "interval_signs": [_sign(interval) for interval in intervals],
                "contour": classify_contour(valid_midis),
                "step_ratio": round(sum(abs(interval) <= 2 for interval in intervals) / max(1, len(intervals)), 4),
                "repetition_ratio": round(_repetition_ratio(signature), 4),
                "motif_signature": signature,
            }
        )
    voice_analyses.sort(
        key=lambda item: (
            item["staff"] != "right_hand",
            -int(item["note_count"]),
            -float(item["mean_pitch"]),
            item["voice_id"],
        )
    )
    primary = voice_analyses[0] if voice_analyses else None
    measures = sorted({context.measure for context in selected})
    register_by_measure: list[dict[str, Any]] = []
    for measure in measures:
        values = [
            parse_pitch_name(str(context.event.get("pitch", "")))
            for context in selected
            if context.measure == measure and context.staff == (primary or {}).get("staff")
        ]
        midis = [int(value) for value in values if value is not None]
        register_by_measure.append({"measure": measure, "mean_pitch": round(mean(midis), 4) if midis else None})
    payload = {
        "analysis_version": "0.2.0",
        "selected_note_count": len(selected),
        "measure_count": len(measures),
        "measures": measures,
        "primary_voice_id": primary["voice_id"] if primary else None,
        "source_motif": {
            "intervals": list((primary or {}).get("intervals", [])[:4]),
            "interval_signs": list((primary or {}).get("interval_signs", [])[:4]),
            "signature": list((primary or {}).get("motif_signature", [])[:4]),
            "contour": (primary or {}).get("contour", "none"),
        },
        "register_by_measure": register_by_measure,
        "voices": voice_analyses,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["fingerprint"] = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
    return payload


def classify_contour(midis: list[int]) -> str:
    """Classify a short pitch series into one auditable contour family."""

    if len(midis) < 2 or max(midis) - min(midis) <= 2:
        return "static"
    peak = max(range(len(midis)), key=midis.__getitem__)
    valley = min(range(len(midis)), key=midis.__getitem__)
    if 0 < peak < len(midis) - 1 and midis[peak] - max(midis[0], midis[-1]) >= 3:
        return "arch"
    if 0 < valley < len(midis) - 1 and min(midis[0], midis[-1]) - midis[valley] >= 3:
        return "valley"
    if midis[-1] - midis[0] >= 3:
        return "ascending"
    if midis[0] - midis[-1] >= 3:
        return "descending"
    return "wave"


def _motif_signature(intervals: list[int], *, length: int = 4) -> list[int]:
    return [max(-7, min(7, int(interval))) for interval in intervals[:length]]


def _repetition_ratio(signature: list[int]) -> float:
    if len(signature) < 2:
        return 0.0
    signs = [_sign(interval) for interval in signature]
    counts = Counter(signs)
    return max(counts.values()) / len(signs)


def _sign(value: int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0

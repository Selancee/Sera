"""Lightweight symbolic fingerprints for candidate novelty scoring."""

from __future__ import annotations

import hashlib
from typing import Any


def score_document_fingerprint(score_document: dict[str, Any] | None) -> str:
    """Return a stable compact fingerprint for a ScoreDocument-like payload."""

    if not score_document:
        return ""
    tokens: list[str] = []
    for measure in score_document.get("measures", []):
        tokens.append(f"m{int(measure.get('number', 0) or 0)}:{measure.get('harmony', '')}:{measure.get('cadence', '')}")
        for event in sorted(
            measure.get("events", []),
            key=lambda item: (
                str(item.get("staff", "")),
                int(item.get("voice", 1) or 1),
                float(item.get("offset", 0.0) or 0.0),
                str(item.get("pitch", "")),
            ),
        ):
            tokens.append(
                "|".join(
                    [
                        str(event.get("staff", "")),
                        str(event.get("voice", 1)),
                        str(event.get("type", "note")),
                        str(event.get("pitch", "")),
                        str(event.get("duration", "")),
                        str(round(float(event.get("offset", 0.0) or 0.0), 3)),
                    ]
                )
            )
    digest = hashlib.sha256("\n".join(tokens).encode("utf-8")).hexdigest()
    return digest[:24]


def score_document_fingerprint_parts(score_document: dict[str, Any] | None) -> dict[str, str]:
    """Return separate final-score fingerprints for melody, rhythm, and harmony."""

    if not score_document:
        return {"melody": "", "rhythm": "", "harmony": ""}
    melody: list[str] = []
    rhythm: list[str] = []
    harmony: list[str] = []
    for measure in score_document.get("measures", []):
        number = int(measure.get("number", 0) or 0)
        harmony.append(f"m{number}:{measure.get('harmony', '')}:{measure.get('cadence', '')}")
        for event in sorted(
            measure.get("events", []),
            key=lambda item: (str(item.get("staff", "")), int(item.get("voice", 1) or 1), float(item.get("offset", 0.0) or 0.0), str(item.get("pitch", ""))),
        ):
            staff = str(event.get("staff", ""))
            if staff == "right_hand" and event.get("type") != "rest":
                melody.append(f"{number}:{event.get('pitch', '')}:{round(float(event.get('offset', 0.0) or 0.0), 3)}")
            rhythm.append(f"{number}:{staff}:{event.get('duration', '')}:{round(float(event.get('offset', 0.0) or 0.0), 3)}")
            if staff == "left_hand" and event.get("type") != "rest":
                harmony.append(f"{number}:{round(float(event.get('offset', 0.0) or 0.0), 3)}:{event.get('pitch', '')}:{event.get('duration', '')}")
    return {
        "melody": _digest(melody),
        "rhythm": _digest(rhythm),
        "harmony": _digest(harmony),
    }


def novelty_scores(fingerprints: list[str]) -> list[float]:
    """Score each candidate by whether its fingerprint is distinct in the set."""

    counts: dict[str, int] = {}
    for fingerprint in fingerprints:
        counts[fingerprint] = counts.get(fingerprint, 0) + 1
    return [1.0 if fingerprint and counts.get(fingerprint, 0) == 1 else 0.35 for fingerprint in fingerprints]


def _digest(tokens: list[str]) -> str:
    if not tokens:
        return ""
    return hashlib.sha256("\n".join(tokens).encode("utf-8")).hexdigest()[:24]

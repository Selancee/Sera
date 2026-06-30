"""Melody fragment generation task builder."""

from __future__ import annotations


def build_melody_fragment_examples(events: list[str], metadata: dict | None = None) -> list[dict]:
    """Create melody-fragment input/target pairs from structured events."""

    meta = metadata or {}
    examples: list[dict] = []
    for index, bar in enumerate(_bars(events), start=1):
        rhythms = [token for token in bar if token.startswith("RHYTHM_")][:8]
        notes = [token for token in bar if token.startswith("NOTE_")][:8]
        if not notes:
            continue
        examples.append(
            {
                "task_type": "melody_fragment_generation",
                "input_tokens": [
                    "TASK_MELODY_FRAGMENT",
                    _first(events, "KEY_", "KEY_C_MAJOR"),
                    _first(events, "METER_", "METER_4_4"),
                    _first(bar, "HARMONY_", "HARMONY_I"),
                    "RHYTHMIC_DENSITY_medium",
                    "MELODIC_CONTOUR_wave",
                    "INTERVAL_PROFILE_mixed",
                    _first(bar, "CADENCE_", "CADENCE_NONE"),
                    "RHYTHM_PATTERN",
                    *rhythms,
                ],
                "target_tokens": notes,
                "teacher_forcing": True,
                "metadata": {**meta, "bar_index": index},
            }
        )
    return examples


def _bars(events: list[str]) -> list[list[str]]:
    bars: list[list[str]] = []
    current: list[str] = []
    for token in events:
        if token == "BAR":
            if current:
                bars.append(current)
            current = ["BAR"]
        elif token == "END":
            continue
        elif current:
            current.append(token)
    if current:
        bars.append(current)
    return bars


def _first(tokens: list[str], prefix: str, fallback: str) -> str:
    return next((token for token in tokens if token.startswith(prefix)), fallback)

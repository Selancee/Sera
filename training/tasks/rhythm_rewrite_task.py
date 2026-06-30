"""Rhythm rewrite task builder."""

from __future__ import annotations

from training.augmentation.rhythm_augmentation import augment_rhythm_events


def build_rhythm_rewrite_examples(events: list[str], metadata: dict | None = None) -> list[dict]:
    """Create rhythm-rewrite examples from repeated rhythm patterns."""

    meta = metadata or {}
    rhythms = [token for token in events if token.startswith("RHYTHM_")][:8]
    if len(rhythms) < 4:
        return []
    rewritten, _ = augment_rhythm_events(rhythms)
    return [
        {
            "task_type": "rhythm_rewrite",
            "input_tokens": [
                "TASK_RHYTHM_REWRITE",
                "ORIGINAL_RHYTHM",
                *rhythms,
                "TARGET_DENSITY_medium",
                _first(events, "METER_", "METER_4_4"),
            ],
            "target_tokens": [token for token in rewritten if token.startswith("RHYTHM_")],
            "teacher_forcing": True,
            "metadata": meta,
        }
    ]


def _first(tokens: list[str], prefix: str, fallback: str) -> str:
    return next((token for token in tokens if token.startswith(prefix)), fallback)

"""Cadence generation task builder."""

from __future__ import annotations


def build_cadence_generation_examples(events: list[str], metadata: dict | None = None) -> list[dict]:
    """Create cadence-generation examples from phrase endings."""

    meta = metadata or {}
    notes = [token for token in events if token.startswith("NOTE_")]
    if len(notes) < 4:
        return []
    cadence_notes = notes[-4:]
    cadence = "CADENCE_AUTHENTIC" if "CADENCE_AUTHENTIC" in events else "CADENCE_HALF"
    return [
        {
            "task_type": "cadence_generation",
            "input_tokens": [
                "TASK_CADENCE",
                _first(events, "KEY_", "KEY_C_MAJOR"),
                "HARMONY",
                "V",
                "I",
                cadence,
                "DIFFICULTY_intermediate",
            ],
            "target_tokens": cadence_notes,
            "teacher_forcing": True,
            "metadata": meta,
        }
    ]


def _first(tokens: list[str], prefix: str, fallback: str) -> str:
    return next((token for token in tokens if token.startswith(prefix)), fallback)

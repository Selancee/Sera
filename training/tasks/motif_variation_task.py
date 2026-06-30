"""Motif variation task builder."""

from __future__ import annotations

from training.augmentation.motif_augmentation import augment_motif_events


def build_motif_variation_examples(events: list[str], metadata: dict | None = None) -> list[dict]:
    """Create motif-variation examples from the first short motif."""

    meta = metadata or {}
    notes = [token for token in events if token.startswith("NOTE_")][:4]
    if len(notes) < 3:
        return []
    examples = []
    for strategy in ["sequence_down", "sequence_up", "inversion", "rhythmic_variation"]:
        varied, _ = augment_motif_events(notes, strategy)
        examples.append(
            {
                "task_type": "motif_variation",
                "input_tokens": [
                    "TASK_MOTIF_VARIATION",
                    "ORIGINAL_MOTIF",
                    *notes,
                    f"STRATEGY_{strategy}",
                    _first(events, "KEY_", "KEY_C_MAJOR"),
                ],
                "target_tokens": [token for token in varied if token.startswith("NOTE_")],
                "teacher_forcing": True,
                "metadata": {**meta, "strategy": strategy},
            }
        )
    return examples


def _first(tokens: list[str], prefix: str, fallback: str) -> str:
    return next((token for token in tokens if token.startswith(prefix)), fallback)

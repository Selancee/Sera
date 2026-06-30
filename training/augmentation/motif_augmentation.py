"""Motif augmentation for V0.5 structured event tokens."""

from __future__ import annotations

from evaluation.analysis.music_statistics import midi_to_pitch, parse_pitch_name
from training.tokenization.structured_events import decode_note_token, note_token


def augment_motif_events(events: list[str], strategy: str = "sequence_up") -> tuple[list[str], dict]:
    """Apply a simple motif transformation to NOTE tokens."""

    output = list(events)
    note_indexes = [index for index, token in enumerate(output) if token.startswith("NOTE_")]
    if not note_indexes:
        return output, {"augmentation": "motif", "strategy": strategy, "changed_notes": 0}
    midis = [_midi(output[index]) for index in note_indexes]
    valid = [midi for midi in midis if midi is not None]
    center = round(sum(valid) / len(valid)) if valid else 60
    changed = 0
    for pos, index in enumerate(note_indexes):
        midi = _midi(output[index])
        if midi is None:
            continue
        if strategy == "repeat":
            shifted = midi
        elif strategy == "sequence_down":
            shifted = midi - 2
        elif strategy == "inversion":
            shifted = center - (midi - center)
        elif strategy == "rhythmic_variation":
            shifted = midi + (2 if pos % 2 else 0)
        elif strategy == "ending_variation":
            shifted = midi + (5 if pos >= len(note_indexes) - 2 else 0)
        else:
            shifted = midi + 2
        output[index] = note_token(midi_to_pitch(_clamp(shifted)))
        changed += output[index] != events[index]
    return output, {"augmentation": "motif", "strategy": strategy, "changed_notes": changed}


def _midi(token: str) -> int | None:
    return parse_pitch_name(decode_note_token(token) or "")


def _clamp(midi: int) -> int:
    while midi < 21:
        midi += 12
    while midi > 108:
        midi -= 12
    return midi

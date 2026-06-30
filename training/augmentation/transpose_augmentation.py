"""Transpose structured MusicXML samples for Sera V0.5."""

from __future__ import annotations

from training.tokenization.musicxml_to_structured_events import musicxml_to_structured_events
from training.tokenization.structured_events import key_token, transpose_pitch_token
from training.tokenization.structured_events_to_musicxml import structured_events_to_musicxml


MAJOR_TARGETS = ["C major", "D major", "E major", "F major", "G major", "A major", "Bb major"]
MINOR_TARGETS = ["A minor", "B minor", "C minor", "D minor", "E minor", "F# minor", "G minor"]
ROOT_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def transpose_musicxml_text(text: str, target_key: str) -> tuple[str, dict]:
    """Transpose MusicXML to a target key using structured event tokens."""

    sequence = musicxml_to_structured_events(text)
    source_key = str(sequence.metadata.get("key", "C major"))
    semitones = _key_delta(source_key, target_key)
    events: list[str] = []
    for token in sequence.events:
        if token.startswith("KEY_"):
            events.append(key_token(target_key))
        else:
            events.append(transpose_pitch_token(token, semitones))
    return structured_events_to_musicxml(events, title=f"Transposed to {target_key}"), {
        "augmentation": "transpose",
        "source_key": source_key,
        "target_key": target_key,
        "semitones": semitones,
    }


def target_keys_for_source(source_key: str) -> list[str]:
    """Return the V0.5 target key set for major or minor input."""

    return MINOR_TARGETS if "minor" in source_key.lower() else MAJOR_TARGETS


def _key_delta(source_key: str, target_key: str) -> int:
    source_root = source_key.split()[0].replace("-flat", "b")
    target_root = target_key.split()[0].replace("-flat", "b")
    return ROOT_PC.get(target_root, 0) - ROOT_PC.get(source_root, 0)

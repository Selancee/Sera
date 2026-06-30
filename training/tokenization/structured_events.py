"""Structured event vocabulary for Sera V0.5.

V0.5 separates pitch, rhythm, position, harmony, section, cadence, and texture
so the small model can learn local musical choices instead of full MusicXML.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from evaluation.analysis.music_statistics import midi_to_pitch, parse_pitch_name


DURATION_TO_TOKEN = {
    "quarter": "RHYTHM_QUARTER",
    "eighth": "RHYTHM_EIGHTH",
    "sixteenth": "RHYTHM_SIXTEENTH",
    "dotted_quarter": "RHYTHM_DOTTED_QUARTER",
    "half": "RHYTHM_HALF",
    "rest_quarter": "RHYTHM_REST_QUARTER",
}
TOKEN_TO_DURATION = {
    "RHYTHM_QUARTER": 1.0,
    "RHYTHM_EIGHTH": 0.5,
    "RHYTHM_SIXTEENTH": 0.25,
    "RHYTHM_DOTTED_QUARTER": 1.5,
    "RHYTHM_HALF": 2.0,
    "RHYTHM_REST_QUARTER": 1.0,
}
CONTROL_DEFAULTS = {
    "rhythmic_density": "medium",
    "melodic_contour": "wave",
    "interval_profile": "mixed",
    "cadence": "none",
    "polyphony": "monophonic",
    "tension": "medium",
    "motif_id": "A",
    "motif_strategy": "repeat",
}
VALID_DENSITIES = {"low", "medium", "high"}
VALID_CONTOURS = {"ascending", "descending", "arch", "wave", "static"}
VALID_INTERVAL_PROFILES = {"stepwise", "mixed", "leaping"}
VALID_CADENCES = {"none", "half", "authentic"}
VALID_POLYPHONY = {"monophonic", "dyadic", "chordal"}
VALID_TENSIONS = {"low", "medium", "high"}
VALID_MOTIF_STRATEGIES = {
    "repeat",
    "sequence_up",
    "sequence_down",
    "inversion",
    "rhythmic_variation",
    "cadence",
}


@dataclass(slots=True)
class StructuredEventSequence:
    """A token sequence plus source metadata."""

    events: list[str]
    metadata: dict[str, object]


def key_token(key: str) -> str:
    """Return a normalized KEY_* token."""

    clean = (key or "C major").replace("-flat", "b").replace(" ", "_").upper()
    return f"KEY_{clean}"


def meter_token(meter: str) -> str:
    """Return a normalized METER_* token."""

    clean = (meter or "4/4").replace("/", "_")
    return f"METER_{clean}"


def tempo_token(tempo: int | str) -> str:
    """Return a TEMPO_* token."""

    try:
        value = int(tempo)
    except (TypeError, ValueError):
        value = 72
    return f"TEMPO_{max(40, min(220, value))}"


def section_token(section: str) -> str:
    return f"SECTION_{(section or 'A').upper()}"


def harmony_token(harmony: str) -> str:
    clean = (harmony or "I").replace(" ", "_")
    return f"HARMONY_{clean}"


def position_token(offset_quarter: float) -> str:
    """Map a quarter offset to a compact POSITION token."""

    rounded = round(float(offset_quarter) * 4) / 4
    label = str(rounded).replace(".0", "").replace(".", "_")
    if label == "0":
        return "POSITION_0"
    return f"POSITION_{label}"


def rhythm_token(duration_name: str, is_rest: bool = False) -> str:
    """Return a RHYTHM_* token for a parsed duration."""

    name = duration_name.replace("rest_", "")
    if is_rest and name == "quarter":
        return "RHYTHM_REST_QUARTER"
    return DURATION_TO_TOKEN.get(name, "RHYTHM_QUARTER")


def note_token(pitch: str) -> str:
    return f"NOTE_{pitch.replace('#', 'SHARP').replace('b', 'FLAT')}"


def chord_token(pitches: Iterable[str]) -> str:
    clean = [pitch.replace("#", "SHARP").replace("b", "FLAT") for pitch in pitches]
    return "CHORD_" + "_".join(clean)


def dynamic_token(dynamic: str = "mf") -> str:
    clean = (dynamic or "mf").upper()
    return f"DYNAMIC_{clean if clean in {'P', 'MP', 'MF', 'F'} else 'MF'}"


def cadence_token(cadence: str = "none") -> str:
    clean = (cadence or "none").replace(" cadence", "").upper()
    if clean not in {"NONE", "HALF", "AUTHENTIC"}:
        clean = "NONE"
    return f"CADENCE_{clean}"


def motif_token(motif_id: str = "A", variation: bool = False) -> str:
    clean = (motif_id or "A").replace("_var", "_VARIATION").upper()
    if variation and "VARIATION" not in clean:
        clean = f"{clean}_VARIATION"
    return f"MOTIF_{clean}"


def texture_token(texture: str = "melody") -> str:
    clean = (texture or "melody").lower()
    if "arpegg" in clean:
        return "TEXTURE_ARPEGGIATED"
    if "chord" in clean:
        return "TEXTURE_CHORDAL"
    return "TEXTURE_MELODY"


def decode_note_token(token: str) -> str | None:
    """Decode NOTE_* or chord pitch fragments back to compact pitch names."""

    if token.startswith("NOTE_"):
        raw = token.removeprefix("NOTE_")
    else:
        raw = token
    return raw.replace("SHARP", "#").replace("FLAT", "b")


def transpose_pitch_token(token: str, semitones: int) -> str:
    """Transpose NOTE_* or CHORD_* tokens while keeping them in piano range."""

    if token.startswith("NOTE_"):
        pitch = decode_note_token(token)
        midi = parse_pitch_name(pitch or "")
        if midi is None:
            return token
        return note_token(midi_to_pitch(_clamp_piano(midi + semitones)))
    if token.startswith("CHORD_"):
        pitches = [decode_note_token(part) or "C4" for part in token.removeprefix("CHORD_").split("_")]
        shifted: list[str] = []
        for pitch in pitches:
            midi = parse_pitch_name(pitch)
            shifted.append(midi_to_pitch(_clamp_piano((midi if midi is not None else 60) + semitones)))
        return chord_token(shifted)
    return token


def normalize_control_value(field: str, value: str | None) -> str:
    """Normalize V0.5 control labels with safe defaults."""

    clean = str(value or CONTROL_DEFAULTS[field]).replace("-", "_").replace(" ", "_").lower()
    valid = {
        "rhythmic_density": VALID_DENSITIES,
        "melodic_contour": VALID_CONTOURS,
        "interval_profile": VALID_INTERVAL_PROFILES,
        "cadence": VALID_CADENCES,
        "polyphony": VALID_POLYPHONY,
        "tension": VALID_TENSIONS,
        "motif_strategy": VALID_MOTIF_STRATEGIES,
    }.get(field)
    if valid and clean not in valid:
        return CONTROL_DEFAULTS[field]
    if field == "motif_id":
        return clean.upper().replace("A_VAR", "A_var")
    return clean


def _clamp_piano(midi: int) -> int:
    while midi < 21:
        midi += 12
    while midi > 108:
        midi -= 12
    return midi

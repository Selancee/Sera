"""Cadence augmentation for Sera V0.5 structured events."""

from __future__ import annotations


CADENCE_PATTERNS = {
    "half": ["CADENCE_HALF", "POSITION_2", "RHYTHM_QUARTER", "NOTE_D5", "POSITION_3", "RHYTHM_QUARTER", "NOTE_G4"],
    "authentic": ["CADENCE_AUTHENTIC", "POSITION_2", "RHYTHM_QUARTER", "NOTE_G4", "POSITION_3", "RHYTHM_QUARTER", "NOTE_C5"],
    "deceptive": ["CADENCE_AUTHENTIC", "POSITION_2", "RHYTHM_QUARTER", "NOTE_B4", "POSITION_3", "RHYTHM_QUARTER", "NOTE_A4"],
    "plagal": ["CADENCE_AUTHENTIC", "POSITION_2", "RHYTHM_QUARTER", "NOTE_F4", "POSITION_3", "RHYTHM_QUARTER", "NOTE_C5"],
}


def augment_cadence_events(events: list[str], cadence_type: str = "authentic") -> tuple[list[str], dict]:
    """Insert or strengthen a simplified cadence before END."""

    pattern = CADENCE_PATTERNS.get(cadence_type, CADENCE_PATTERNS["authentic"])
    output = [token for token in events if token not in {"CADENCE_NONE"}]
    insert_at = output.index("END") if "END" in output else len(output)
    output[insert_at:insert_at] = pattern
    return output, {"augmentation": "cadence", "cadence_type": cadence_type, "inserted_tokens": len(pattern)}

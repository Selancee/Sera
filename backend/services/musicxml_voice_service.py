"""Translate between Sera staff-local voices and MusicXML part voices.

MusicXML identifies a voice within a complete ``part``, not within one staff.
MuseScore consequently exports its four voices per staff as 1..4 for staff 1,
5..8 for staff 2, and so on. Sera's canonical model intentionally keeps the
editor-facing voice number local to the staff, so this boundary needs an
explicit, reversible mapping.
"""

from __future__ import annotations


VOICES_PER_STAFF = 4


def musicxml_voice_for_staff(local_voice: int, staff_number: int) -> int:
    """Return the part-wide MusicXML voice for one staff-local Sera voice."""

    voice = int(local_voice)
    staff = int(staff_number)
    if voice < 1 or voice > VOICES_PER_STAFF:
        raise ValueError(f"staff-local voice must be between 1 and {VOICES_PER_STAFF}: {voice}")
    if staff < 1:
        raise ValueError(f"staff number must be positive: {staff}")
    return (staff - 1) * VOICES_PER_STAFF + voice


def local_voice_from_musicxml(musicxml_voice: int) -> int:
    """Return the staff-local Sera voice encoded by a MusicXML part voice."""

    voice = int(musicxml_voice)
    if voice < 1:
        raise ValueError(f"MusicXML voice number must be positive: {voice}")
    return ((voice - 1) % VOICES_PER_STAFF) + 1

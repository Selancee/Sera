"""Compatibility wrapper for V0.94 beaming metadata."""

from __future__ import annotations

from typing import Any

from backend.notation.beaming import assign_beams_to_measure


def annotate_beam_groups(events: list[dict[str, Any]], meter: str) -> list[dict[str, Any]]:
    """Attach meter-aware beam groups without changing musical content."""

    return assign_beams_to_measure(events, meter)

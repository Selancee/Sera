"""Phrase utilities for V0.9 generation."""

from __future__ import annotations


def phrase_number(measure_number: int, phrase_length: int = 4) -> int:
    return ((measure_number - 1) // max(1, phrase_length)) + 1

"""Deterministic routing for creative edits that need the Composer pipeline."""

from __future__ import annotations

import re


_CREATIVE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(?:重写|改写|重构|重做|重新创作|创作).{0,8}(?:旋律|主题|动机)",
        r"(?:旋律|主题|动机).{0,8}(?:重写|改写|重构|变奏|发展|重新创作)",
        r"(?:重新和声化|重配和声|改写和声|和声变奏)",
        r"\b(?:rewrite|recompose|compose|regenerate)\b.{0,32}\b(?:melody|theme|motif)\b",
        r"\b(?:melody|theme|motif)\b.{0,32}\b(?:rewrite|variation|development|recomposition)\b",
        r"\b(?:reharmonize|reharmonise|reharmonization|reharmonisation)\b",
    )
)


def is_compositional_edit_instruction(instruction: str) -> bool:
    """Return whether an explicit instruction needs new pitch realization.

    The router intentionally requires an explicit creative verb plus a musical
    object. Vague aesthetic requests remain unsupported instead of being
    silently interpreted as permission to rewrite notes.
    """

    text = " ".join(instruction.strip().split())
    return bool(text and any(pattern.search(text) for pattern in _CREATIVE_PATTERNS))


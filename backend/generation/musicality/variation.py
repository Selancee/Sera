"""Stable variation helpers for musicality engines."""

from __future__ import annotations

import hashlib


def variation_int(seed: str | None, salt: str = "") -> int:
    """Return a deterministic integer for a seed/salt pair."""

    text = f"{seed or ''}:{salt}"
    if not text.strip(":"):
        return 0
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def variation_offset(seed: str | None, modulo: int, salt: str = "") -> int:
    if modulo <= 0:
        return 0
    return variation_int(seed, salt) % modulo

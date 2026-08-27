"""Run-level seed utilities for generation variety."""

from __future__ import annotations

import hashlib
import random
import time
import uuid
from typing import Any


def create_run_seed(raw_prompt: str | None = None, controls: dict[str, Any] | None = None) -> int:
    """Create a positive 63-bit seed.

    If controls include an explicit seed-like value, the same value is mapped to
    the same integer seed. Otherwise a nonce is mixed in so repeated generations
    of the same prompt naturally differ.
    """

    controls = controls or {}
    explicit = controls.get("run_seed") or controls.get("variation_seed") or controls.get("seed")
    if explicit not in {None, ""}:
        return _seed_from_text(str(explicit))
    nonce = f"{time.time_ns()}:{uuid.uuid4().hex}"
    return _seed_from_text(f"{raw_prompt or ''}:{_stable_controls(controls)}:{nonce}")


def create_variant_id(run_seed: int, index: int | None = None) -> str:
    suffix = "" if index is None else f":{int(index)}"
    digest = hashlib.sha256(f"{int(run_seed)}{suffix}".encode("utf-8")).hexdigest()[:10]
    return f"variant_{digest}"


def make_seeded_rng(run_seed: int, namespace: str) -> random.Random:
    seed = _seed_from_text(f"{int(run_seed)}:{namespace}")
    return random.Random(seed)


def _seed_from_text(text: str) -> int:
    digest = hashlib.sha256(str(text).encode("utf-8")).hexdigest()
    return int(digest[:16], 16) & ((1 << 63) - 1)


def _stable_controls(controls: dict[str, Any]) -> str:
    items = []
    for key in sorted(controls):
        if key in {"run_seed", "variation_seed", "seed"}:
            continue
        items.append(f"{key}={controls[key]}")
    return "|".join(items)

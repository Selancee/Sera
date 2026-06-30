"""Constrained decoding utilities for Sera V0.5 local symbolic tasks."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(slots=True)
class DecodingConfig:
    """Sampling and music-aware decoding controls."""

    temperature: float = 1.15
    top_p: float = 0.92
    top_k: int = 60
    repetition_penalty: float = 1.2
    no_repeat_ngram_size: int = 4
    duration_diversity_penalty: bool = True
    max_consecutive_same_duration: int = 3
    max_consecutive_stepwise_motion: int = 4
    pitch_range_penalty: bool = True
    cadence_bias: float = 0.2

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def filter_token_candidates(
    candidates: dict[str, float],
    history: list[str],
    config: DecodingConfig | None = None,
) -> dict[str, float]:
    """Apply repetition, n-gram, duration, range, and cadence constraints."""

    cfg = config or DecodingConfig()
    adjusted = dict(candidates)
    for token in list(adjusted):
        if token in history and cfg.repetition_penalty > 1.0:
            adjusted[token] /= cfg.repetition_penalty
        if _would_repeat_ngram(history, token, cfg.no_repeat_ngram_size):
            adjusted[token] = -math.inf
        if cfg.duration_diversity_penalty and token.startswith("RHYTHM_"):
            run = _consecutive_run(history, token)
            if run >= cfg.max_consecutive_same_duration:
                adjusted[token] = -math.inf
            elif run:
                adjusted[token] -= 0.25 * run
        if token.startswith("NOTE_") and cfg.pitch_range_penalty and _outside_soft_range(token):
            adjusted[token] -= 1.0
        if token in {"NOTE_C4", "NOTE_C5", "CADENCE_AUTHENTIC"} and _near_end(history):
            adjusted[token] += cfg.cadence_bias
    return adjusted


def sample_token(
    candidates: dict[str, float],
    history: list[str] | None = None,
    config: DecodingConfig | None = None,
    rng: random.Random | None = None,
) -> str:
    """Sample one token from logits with temperature, top-k, and top-p."""

    cfg = config or DecodingConfig()
    random_source = rng or random.Random()
    adjusted = filter_token_candidates(candidates, history or [], cfg)
    finite = [(token, score) for token, score in adjusted.items() if math.isfinite(score)]
    if not finite:
        return max(candidates.items(), key=lambda item: item[1])[0]
    finite.sort(key=lambda item: item[1], reverse=True)
    if cfg.top_k > 0:
        finite = finite[: cfg.top_k]
    probs = _softmax([(token, score / max(0.05, cfg.temperature)) for token, score in finite])
    cumulative = 0.0
    nucleus: list[tuple[str, float]] = []
    for token, prob in probs:
        cumulative += prob
        nucleus.append((token, prob))
        if cumulative >= cfg.top_p:
            break
    total = sum(prob for _, prob in nucleus) or 1.0
    threshold = random_source.random()
    running = 0.0
    for token, prob in nucleus:
        running += prob / total
        if threshold <= running:
            return token
    return nucleus[-1][0]


def enforce_decoding_constraints(tokens: Iterable[str], config: DecodingConfig | None = None) -> list[str]:
    """Remove tokens that violate hard duration and no-repeat constraints."""

    cfg = config or DecodingConfig()
    output: list[str] = []
    for token in tokens:
        if token.startswith("RHYTHM_") and _consecutive_run(output, token) >= cfg.max_consecutive_same_duration:
            output.append("RHYTHM_EIGHTH" if token != "RHYTHM_EIGHTH" else "RHYTHM_QUARTER")
            continue
        if _would_repeat_ngram(output, token, cfg.no_repeat_ngram_size):
            continue
        output.append(token)
    return output


def _softmax(items: list[tuple[str, float]]) -> list[tuple[str, float]]:
    max_score = max(score for _, score in items)
    exp = [(token, math.exp(score - max_score)) for token, score in items]
    total = sum(value for _, value in exp) or 1.0
    return [(token, value / total) for token, value in exp]


def _would_repeat_ngram(history: list[str], token: str, size: int) -> bool:
    if size <= 1 or len(history) < size - 1:
        return False
    candidate = tuple([*history[-(size - 1) :], token])
    existing = {tuple(history[index : index + size]) for index in range(0, max(0, len(history) - size + 1))}
    return candidate in existing


def _consecutive_run(history: list[str], token: str) -> int:
    run = 0
    for item in reversed(history):
        if item != token:
            break
        run += 1
    return run


def _outside_soft_range(token: str) -> bool:
    import re

    match = re.search(r"([A-G](?:SHARP|FLAT)?)(-?\d+)$", token)
    if not match:
        return False
    octave = int(match.group(2))
    return octave < 3 or octave > 6


def _near_end(history: list[str]) -> bool:
    return "CADENCE_HALF" in history[-8:] or "CADENCE_AUTHENTIC" in history[-8:] or len(history) > 24

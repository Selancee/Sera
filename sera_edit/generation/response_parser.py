"""Deterministic extraction helpers for provider text responses."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_json_object(raw_text: str) -> dict[str, Any] | None:
    """Parse a JSON object, allowing only harmless code-fence/explanatory wrappers."""

    text = raw_text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def extract_musicxml(raw_text: str) -> str:
    """Extract one complete MusicXML document using baseline-permitted cleanup only."""

    text = raw_text.strip().lstrip("\ufeff")
    fenced = re.fullmatch(r"```(?:xml|musicxml)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    starts = [index for marker in ("<?xml", "<score-partwise", "<score-timewise") if (index := text.find(marker)) >= 0]
    if starts:
        text = text[min(starts) :]
    for closing in ("</score-partwise>", "</score-timewise>"):
        end = text.rfind(closing)
        if end >= 0:
            return text[: end + len(closing)].strip()
    return text

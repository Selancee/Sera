"""Prompt term extraction for raw user prompts.

This module is intentionally deterministic and dependency-light.  It preserves
raw prompt wording while exposing normalized musical terms for conflict
resolution, style mapping, and plan grounding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PromptTermDefinition:
    term: str
    normalized: str
    category: str
    confidence: float = 1.0


TERM_DEFINITIONS: tuple[PromptTermDefinition, ...] = (
    # Cyberpunk / electronic custom style.
    PromptTermDefinition("cyberpunk", "cyberpunk", "style"),
    PromptTermDefinition("\u8d5b\u535a\u670b\u514b", "cyberpunk", "style"),
    PromptTermDefinition("sci fi", "futuristic", "style"),
    PromptTermDefinition("sci-fi", "futuristic", "style"),
    PromptTermDefinition("\u79d1\u5e7b", "futuristic", "style"),
    PromptTermDefinition("\u672a\u6765\u611f", "futuristic", "style"),
    PromptTermDefinition("\u673a\u68b0\u611f", "mechanical", "mood"),
    PromptTermDefinition("mechanical", "mechanical", "mood"),
    PromptTermDefinition("\u51b7\u8272", "cold", "mood"),
    PromptTermDefinition("cold", "cold", "mood"),
    PromptTermDefinition("\u6697\u9ed1\u7535\u5b50", "dark_electronic", "style"),
    PromptTermDefinition("\u7535\u5b50", "electronic", "style"),
    PromptTermDefinition("electronic", "electronic", "style"),
    PromptTermDefinition("\u91cd\u590d\u4f4e\u97f3", "repeating_bass", "accompaniment"),
    PromptTermDefinition("repeating bass", "repeating_bass", "accompaniment"),
    PromptTermDefinition("\u56fa\u5b9a\u97f3\u578b", "ostinato", "texture"),
    PromptTermDefinition("ostinato", "ostinato", "texture"),
    PromptTermDefinition("\u5207\u5206\u8282\u594f", "syncopation", "rhythm"),
    PromptTermDefinition("syncopated", "syncopation", "rhythm"),
    PromptTermDefinition("syncopation", "syncopation", "rhythm"),
    # Other custom styles.
    PromptTermDefinition("anime", "anime", "style"),
    PromptTermDefinition("\u52a8\u753b\u98ce", "anime", "style"),
    PromptTermDefinition("\u65e5\u7cfb", "anime", "style"),
    PromptTermDefinition("\u4e8c\u6b21\u5143", "anime", "style"),
    PromptTermDefinition("\u660e\u4eae", "bright", "mood"),
    PromptTermDefinition("bright", "bright", "mood"),
    PromptTermDefinition("\u6292\u60c5", "lyrical", "mood"),
    PromptTermDefinition("lyrical", "lyrical", "mood"),
    PromptTermDefinition("game soundtrack", "game", "style"),
    PromptTermDefinition("video game", "game", "style"),
    PromptTermDefinition("\u6e38\u620f\u914d\u4e50", "game", "style"),
    PromptTermDefinition("loopable", "loopable", "form"),
    PromptTermDefinition("\u5faa\u73af\u611f", "loopable", "form"),
    PromptTermDefinition("\u4e3b\u9898\u97f3\u4e50", "theme", "form"),
    PromptTermDefinition("cinematic", "cinematic", "style"),
    PromptTermDefinition("trailer", "cinematic", "style"),
    PromptTermDefinition("\u7535\u5f71\u611f", "cinematic", "style"),
    PromptTermDefinition("\u7535\u5f71\u9884\u544a", "cinematic", "style"),
    PromptTermDefinition("\u5b8f\u5927", "dramatic", "mood"),
    PromptTermDefinition("\u7d27\u5f20", "tense", "mood"),
    PromptTermDefinition("new age", "new_age", "style"),
    PromptTermDefinition("\u65b0\u4e16\u7eaa", "new_age", "style"),
    PromptTermDefinition("ambient", "ambient", "style"),
    PromptTermDefinition("\u6c1b\u56f4", "ambient", "style"),
    PromptTermDefinition("\u7a7a\u7075", "ambient", "mood"),
    PromptTermDefinition("\u67d4\u548c", "gentle", "mood"),
    PromptTermDefinition("\u6e29\u67d4", "gentle", "mood"),
    # Chinese / pentatonic style.
    PromptTermDefinition("chinese", "chinese", "style"),
    PromptTermDefinition("\u4e2d\u56fd\u98ce", "chinese", "style"),
    PromptTermDefinition("\u56fd\u98ce", "chinese", "style"),
    PromptTermDefinition("\u53e4\u98ce", "chinese", "style"),
    PromptTermDefinition("\u4e94\u58f0", "pentatonic", "style"),
    PromptTermDefinition("pentatonic", "pentatonic", "style"),
    PromptTermDefinition("\u6b66\u4fa0", "wuxia", "style"),
    PromptTermDefinition("\u4ed9\u4fa0", "xianxia", "style"),
    # General music controls.
    PromptTermDefinition("romantic", "romantic", "style"),
    PromptTermDefinition("\u6d6a\u6f2b", "romantic", "style"),
    PromptTermDefinition("jazz", "jazz", "style"),
    PromptTermDefinition("\u7235\u58eb", "jazz", "style"),
    PromptTermDefinition("pop", "pop", "style"),
    PromptTermDefinition("\u6d41\u884c", "pop", "style"),
    PromptTermDefinition("classical", "classical", "style"),
    PromptTermDefinition("\u53e4\u5178", "classical", "style"),
    PromptTermDefinition("piano", "piano", "instrumentation"),
    PromptTermDefinition("\u94a2\u7434", "piano", "instrumentation"),
    PromptTermDefinition("synth", "synthesizer", "instrumentation"),
    PromptTermDefinition("\u5408\u6210\u5668", "synthesizer", "instrumentation"),
    PromptTermDefinition("waltz", "waltz", "meter"),
    PromptTermDefinition("\u5706\u821e\u66f2", "waltz", "meter"),
    PromptTermDefinition("arpeggio", "arpeggiated", "texture"),
    PromptTermDefinition("arpeggiated", "arpeggiated", "texture"),
    PromptTermDefinition("\u7406\u97f3", "arpeggiated", "texture"),
    PromptTermDefinition("\u6d41\u52a8", "flowing", "rhythm"),
    PromptTermDefinition("\u9644\u70b9", "dotted", "rhythm"),
)

METER_PATTERN = re.compile(r"\b(3/4|4/4|6/8)\b")
LENGTH_PATTERN = re.compile(r"\b(8|16|32)\s*(?:bars?|measures?)\b", re.I)
CHINESE_LENGTH_PATTERN = re.compile(r"(8|16|32)\s*\u5c0f\u8282")
KEY_PATTERN = re.compile(r"\b([A-G](?:#|b)?)(?:\s+|-)?(major|minor|maj|min)\b", re.I)


class PromptTermExtractor:
    """Extract normalized musical terms from raw prompts."""

    def extract(self, prompt: str) -> dict[str, Any]:
        text = str(prompt or "")
        lowered = _normalize_text(text)
        terms: list[dict[str, Any]] = []
        consumed: list[str] = []
        for definition in TERM_DEFINITIONS:
            if _normalize_text(definition.term) in lowered:
                terms.append(
                    {
                        "term": definition.term,
                        "normalized": definition.normalized,
                        "category": definition.category,
                        "confidence": definition.confidence,
                    }
                )
                consumed.append(definition.term)

        self._append_regex_terms(text, terms, consumed)
        unparsed = _unparsed_terms(text, consumed)
        return {
            "prompt_terms": _dedupe_terms(terms),
            "source_prompt_terms": list(dict.fromkeys(consumed)),
            "unparsed_prompt_terms": unparsed,
            "language": "zh-CN" if _contains_cjk(text) else "en",
        }

    @staticmethod
    def _append_regex_terms(text: str, terms: list[dict[str, Any]], consumed: list[str]) -> None:
        for match in METER_PATTERN.finditer(text):
            value = match.group(1)
            terms.append({"term": value, "normalized": value, "category": "meter", "confidence": 1.0})
            consumed.append(value)
        for pattern in (LENGTH_PATTERN, CHINESE_LENGTH_PATTERN):
            for match in pattern.finditer(text):
                value = match.group(1)
                terms.append({"term": match.group(0), "normalized": value, "category": "length", "confidence": 1.0})
                consumed.append(match.group(0))
        for match in KEY_PATTERN.finditer(text):
            mode = "major" if match.group(2).lower() in {"major", "maj"} else "minor"
            normalized = f"{match.group(1).replace('b', '-flat')} {mode}"
            terms.append({"term": match.group(0), "normalized": normalized, "category": "key", "confidence": 1.0})
            consumed.append(match.group(0))


def extract_prompt_terms(prompt: str) -> dict[str, Any]:
    return PromptTermExtractor().extract(prompt)


def _normalize_text(value: str) -> str:
    return str(value or "").replace("-", " ").replace("_", " ").lower()


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def _dedupe_terms(terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for term in terms:
        key = (str(term.get("term", "")), str(term.get("normalized", "")), str(term.get("category", "")))
        if key in seen:
            continue
        seen.add(key)
        out.append(term)
    return out


def _unparsed_terms(prompt: str, consumed: list[str]) -> list[str]:
    remaining = str(prompt or "")
    for term in sorted(consumed, key=len, reverse=True):
        remaining = remaining.replace(term, " ")
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_ -]{2,}", remaining)
    ignored = {
        "\u5c0f\u8282",
        "\u94a2\u7434",
        "piano",
        "with",
        "and",
        "for",
        "compose",
        "write",
    }
    return [token.strip(" ,.;:，。；：") for token in tokens if token.strip(" ,.;:，。；：").lower() not in ignored]

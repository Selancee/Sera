"""Prompt Understanding Agent for Sera V0.2.

The agent returns deterministic structured JSON fields first, then optionally
merges a live OpenAI-compatible JSON response.  If the LLM call fails or omits
fields, the local rule parser remains the fallback so the app stays demo-ready.
"""

from __future__ import annotations

import json
import re
from typing import Any

from backend.agents.llm_provider import LLMProvider
from backend.generation.musicality.style_profile_mapper import map_style_profile
from backend.models.schemas import StructuredMusicIntent, validate_agent_plan_json
from backend.services.prompt_term_extractor import extract_prompt_terms


STYLE_KEYWORDS: list[tuple[str, str]] = [
    ("中国风", "chinese"),
    ("五声", "chinese"),
    ("国风", "chinese"),
    ("爵士", "jazz"),
    ("jazz", "jazz"),
    ("swing", "jazz"),
    ("blues", "jazz"),
    ("浪漫", "romantic"),
    ("romantic", "romantic"),
    ("chopin", "romantic"),
    ("肖邦", "romantic"),
    ("debussy", "romantic"),
    ("德彪西", "romantic"),
    ("古典", "classical"),
    ("classical", "classical"),
    ("baroque", "classical"),
    ("巴洛克", "classical"),
    ("流行", "pop"),
    ("pop", "pop"),
    ("电子", "electronic"),
    ("electronic", "electronic"),
    ("ambient", "ambient"),
    ("氛围", "ambient"),
    ("minimalist", "minimalist"),
    ("minimal", "minimalist"),
    ("实验", "experimental"),
    ("experimental", "experimental"),
]

MOOD_KEYWORDS: list[tuple[str, str]] = [
    ("忧郁", "melancholic"),
    ("悲伤", "sad"),
    ("sad", "sad"),
    ("melancholic", "melancholic"),
    ("dark", "dark"),
    ("黑暗", "dark"),
    ("明亮", "bright"),
    ("bright", "bright"),
    ("happy", "bright"),
    ("活泼", "energetic"),
    ("energetic", "energetic"),
    ("calm", "calm"),
    ("平静", "calm"),
    ("梦幻", "dreamlike"),
    ("dream", "dreamlike"),
    ("tense", "tense"),
    ("紧张", "tense"),
]

INSTRUMENT_KEYWORDS: list[tuple[str, str]] = [
    ("钢琴", "piano"),
    ("piano", "piano"),
    ("violin", "violin"),
    ("小提琴", "violin"),
    ("cello", "cello"),
    ("大提琴", "cello"),
    ("flute", "flute"),
    ("长笛", "flute"),
    ("clarinet", "clarinet"),
    ("单簧管", "clarinet"),
    ("guitar", "guitar"),
    ("吉他", "guitar"),
    ("strings", "string ensemble"),
    ("弦乐", "string ensemble"),
    ("quartet", "string quartet"),
    ("四重奏", "string quartet"),
    ("synth", "synthesizer"),
    ("合成器", "synthesizer"),
    ("voice", "voice"),
    ("人声", "voice"),
]

TEXTURE_KEYWORDS: list[tuple[str, str]] = [
    ("单声部", "single_line"),
    ("monophonic", "single_line"),
    ("counterpoint", "simple_counterpoint"),
    ("对位", "simple_counterpoint"),
    ("polyphonic", "simple_counterpoint"),
    ("arpeggio", "arpeggiated"),
    ("arpeggiated", "arpeggiated"),
    ("琶音", "arpeggiated"),
    ("流动", "arpeggiated"),
    ("chordal", "chordal"),
    ("和弦式", "chordal"),
    ("柱式", "chordal"),
    ("accompaniment", "melody_accompaniment"),
    ("伴奏", "melody_accompaniment"),
]

DIFFICULTY_KEYWORDS: list[tuple[str, str]] = [
    ("beginner", "beginner"),
    ("初级", "beginner"),
    ("儿童", "beginner"),
    ("simple", "beginner"),
    ("简单", "beginner"),
    ("intermediate", "intermediate"),
    ("中级", "intermediate"),
    ("advanced", "advanced"),
    ("复杂", "advanced"),
    ("hard", "advanced"),
]

KEY_PATTERN = re.compile(r"\b([A-G](?:#|b)?)(?:\s+|-)?(major|minor|maj|min)\b", re.I)
CHINESE_KEY_PATTERN = re.compile(r"\b([A-Ga-g](?:#|b)?)\s*([大小])调")
BPM_PATTERN = re.compile(r"\b(\d{2,3})\s*(?:bpm|beats per minute|拍/分钟)?\b", re.I)
BAR_PATTERN = re.compile(r"\b(8|16|32)\s*(?:bars?|measures?|小节)\b", re.I)
TIME_PATTERN = re.compile(r"\b(3/4|4/4|6/8)\b")
FORM_PATTERN = re.compile(r"\b(AABA|ABA|AB|Theme and Variation)\b", re.I)


def _term_values(terms: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    styles = [str(term.get("normalized")) for term in terms if term.get("category") == "style"]
    if "cyberpunk" in styles or "dark_electronic" in styles:
        values["style"] = "custom"
        values["base_style"] = "electronic"
    textures = [str(term.get("normalized")) for term in terms if term.get("category") == "texture"]
    if "ostinato" in textures:
        values["texture"] = "ostinato"
    elif textures:
        values["texture"] = textures[0]
    moods = [str(term.get("normalized")) for term in terms if term.get("category") == "mood"]
    if moods:
        values["mood"] = "dark" if any(mood in {"cold", "mechanical", "tense"} for mood in moods) else moods[0]
    lengths = [str(term.get("normalized")) for term in terms if term.get("category") == "length"]
    if lengths:
        try:
            values["length_measures"] = int(lengths[0])
        except ValueError:
            pass
    return values


class PromptUnderstandingAgent:
    """Convert natural-language prompts into stable structured music intent."""

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or LLMProvider()

    def understand(self, prompt: str) -> StructuredMusicIntent:
        """Return a schema-compatible intent with deterministic fallbacks."""

        normalized = prompt.strip()
        lower = normalized.lower()
        term_payload = extract_prompt_terms(normalized)
        term_values = _term_values(term_payload.get("prompt_terms", []))

        style = self._first_keyword(lower, STYLE_KEYWORDS, "classical")
        style_mapping = map_style_profile(lower, style)
        base_style = str(style_mapping.get("base_style") or style)
        effective_style = str(style_mapping.get("style") or style)
        mood = str(term_values.get("mood") or self._first_keyword(lower, MOOD_KEYWORDS, "focused"))
        if style_mapping.get("style_profile") and mood == "focused" and any(tag in style_mapping.get("custom_style_tags", []) for tag in ["cold", "dark", "mechanical"]):
            mood = "dark"
        instruments = self._extract_instruments(lower)
        key = self._extract_key(normalized, lower, base_style, mood)
        meter = self._extract_time_signature(lower)
        tempo = self._extract_tempo(lower, base_style, mood)
        length = int(term_values.get("length_measures") or self._extract_bars(lower))
        difficulty = self._first_keyword(lower, DIFFICULTY_KEYWORDS, "intermediate")
        mapped_profile = dict(style_mapping.get("style_profile") or {})
        texture = str(mapped_profile.get("texture") or term_values.get("texture") or self._extract_texture(lower, instruments, difficulty))
        form = self._extract_form(normalized, length)

        intent = StructuredMusicIntent(
            prompt=normalized,
            title=self._title_for_prompt(normalized, base_style, key, meter),
            style=effective_style,
            base_style=base_style,
            custom_style_tags=list(style_mapping.get("custom_style_tags") or []),
            style_profile=dict(style_mapping.get("style_profile") or {}),
            mood=mood,
            key=key,
            time_signature=meter,
            tempo_bpm=tempo,
            bars=length,
            instruments=instruments,
            texture=texture,
            harmony=self._extract_harmony(lower, base_style),
            form=form,
            difficulty=difficulty,
            harmony_plan=self._default_harmony_plan(key, base_style),
            constraints=self._extract_constraints(lower),
            raw_prompt=normalized,
            prompt_terms=list(term_payload.get("prompt_terms") or []),
            source_prompt_terms=list(term_payload.get("source_prompt_terms") or []),
            unparsed_prompt_terms=list(term_payload.get("unparsed_prompt_terms") or []),
        )

        provider_result = self.llm_provider.complete_json(
            (
                "Return only valid JSON for the Sera composition intent schema. "
                "Allowed meter values: 4/4, 3/4, 6/8. Allowed lengths: 8, 16, 32. "
                "Do not include prose outside JSON."
            ),
            normalized,
        )
        intent.llm_provider = provider_result.provider
        intent.llm_model = provider_result.model
        intent.agent_mode = "llm" if provider_result.used_live_provider else "mock"
        if provider_result.used_live_provider:
            self._merge_llm_fields(intent, provider_result.text)
            valid, errors = validate_agent_plan_json(intent.to_agent_plan_json())
            if not valid:
                # TODO: expose schema errors to an agent-debug panel when the UI
                # adds live provider diagnostics.
                intent.revision_goals.extend([f"schema fallback: {error}" for error in errors])
                intent.agent_mode = "hybrid"
        elif provider_result.error:
            intent.revision_goals.append(f"LLM fallback used: {provider_result.error}")
        return intent

    @staticmethod
    def _first_keyword(text: str, mapping: list[tuple[str, str]], fallback: str) -> str:
        for keyword, value in mapping:
            if keyword.lower() in text:
                return value
        return fallback

    @staticmethod
    def _extract_instruments(text: str) -> list[str]:
        found = []
        for keyword, instrument in INSTRUMENT_KEYWORDS:
            if keyword.lower() in text and instrument not in found:
                found.append(instrument)
        return found or ["piano"]

    @staticmethod
    def _extract_key(prompt: str, lower: str, style: str, mood: str) -> str:
        match = KEY_PATTERN.search(prompt)
        if match:
            mode = "major" if match.group(2).lower() in {"major", "maj"} else "minor"
            return f"{match.group(1).replace('b', '-flat')} {mode}"
        chinese_match = CHINESE_KEY_PATTERN.search(prompt)
        if chinese_match:
            mode = "major" if chinese_match.group(2) == "大" else "minor"
            return f"{chinese_match.group(1).upper()} {mode}"
        if "minor" in lower or "小调" in lower or mood in {"sad", "melancholic", "dark"}:
            return "A minor"
        if "major" in lower or "大调" in lower:
            return "C major"
        if style == "jazz":
            return "F major"
        return "C major"

    @staticmethod
    def _extract_time_signature(text: str) -> str:
        match = TIME_PATTERN.search(text)
        if match:
            return match.group(1)
        if "三拍" in text or "waltz" in text or "圆舞曲" in text:
            return "3/4"
        if "6/8" in text or "六八" in text or "jig" in text or "摇篮" in text:
            return "6/8"
        return "4/4"

    @staticmethod
    def _extract_tempo(text: str, style: str, mood: str) -> int:
        match = BPM_PATTERN.search(text)
        if match:
            value = int(match.group(1))
            if 40 <= value <= 220:
                return value
        if "adagio" in text or "慢" in text or mood in {"calm", "melancholic", "sad", "dreamlike"}:
            return 72
        if "快" in text or "allegro" in text or style in {"electronic", "jazz"} or mood == "energetic":
            return 124
        if style == "romantic":
            return 84
        return 90

    @staticmethod
    def _extract_bars(text: str) -> int:
        match = BAR_PATTERN.search(text)
        if match:
            return int(match.group(1))
        if "32" in text or "long" in text or "较长" in text or "development" in text:
            return 32
        if "16" in text or "中等" in text:
            return 16
        if "short" in text or "简短" in text or "sketch" in text:
            return 8
        return 16

    @staticmethod
    def _extract_texture(text: str, instruments: list[str], difficulty: str) -> str:
        for keyword, texture in TEXTURE_KEYWORDS:
            if keyword.lower() in text:
                return texture
        if difficulty == "beginner":
            return "melody_accompaniment"
        if "piano" in instruments:
            return "arpeggiated" if "romantic" in text or "nocturne" in text else "melody_accompaniment"
        return "single_line"

    @staticmethod
    def _extract_harmony(text: str, style: str) -> str:
        if "chromatic" in text or "半音" in text:
            return "chromatic color tones"
        if "modal" in text or "调式" in text or style in {"jazz", "chinese"}:
            return "modal mixture"
        if "blues" in text:
            return "blues dominant cycle"
        return "functional diatonic"

    @staticmethod
    def _extract_form(prompt: str, bars: int) -> str:
        match = FORM_PATTERN.search(prompt)
        if match:
            value = match.group(1)
            return "Theme and Variation" if value.lower().startswith("theme") else value.upper()
        if "变奏" in prompt:
            return "Theme and Variation"
        if bars == 32:
            return "AABA"
        if bars == 16:
            return "ABA"
        return "AB"

    @staticmethod
    def _default_harmony_plan(key: str, style: str) -> list[str]:
        if style == "jazz":
            return ["ii7", "V7", "Imaj7", "VI7"]
        if style == "chinese":
            return ["I", "vi", "IV", "V"]
        if "minor" in key.lower():
            return ["i", "VI", "iv", "V"]
        return ["I", "vi", "IV", "V"]

    @staticmethod
    def _extract_constraints(text: str) -> list[str]:
        constraints = []
        if "editable" in text or "可编辑" in text:
            constraints.append("editable score output")
        if "simple" in text or "简单" in text:
            constraints.append("simple playable rhythm")
        if "no drums" in text or "不要鼓" in text:
            constraints.append("avoid percussion")
        return constraints

    @staticmethod
    def _title_for_prompt(prompt: str, style: str, key: str, meter: str) -> str:
        lower = prompt.lower()
        if "nocturne" in lower or "夜曲" in prompt:
            return f"Nocturne in {key}"
        if "waltz" in lower or "圆舞曲" in prompt:
            return f"Waltz in {key}"
        if style == "chinese":
            return f"Pentatonic Study in {key}"
        if style == "jazz":
            return f"Jazz Sketch in {meter}"
        return f"{style.title()} Sketch in {key}"

    @staticmethod
    def _merge_llm_fields(intent: StructuredMusicIntent, payload: str) -> None:
        try:
            data: dict[str, Any] = json.loads(payload)
        except json.JSONDecodeError:
            return

        field_map = {
            "title": "title",
            "style": "style",
            "base_style": "base_style",
            "mood": "mood",
            "key": "key",
            "meter": "time_signature",
            "time_signature": "time_signature",
            "texture": "texture",
            "form": "form",
            "difficulty": "difficulty",
            "harmony": "harmony",
        }
        for source, target in field_map.items():
            value = data.get(source)
            if isinstance(value, str) and 1 <= len(value) <= 120:
                setattr(intent, target, value)

        tags = data.get("custom_style_tags")
        if isinstance(tags, list):
            intent.custom_style_tags = [str(item)[:40] for item in tags[:12] if str(item).strip()]
        style_profile = data.get("style_profile")
        if isinstance(style_profile, dict):
            intent.style_profile = {str(key): value for key, value in style_profile.items()}

        tempo = data.get("tempo", data.get("tempo_bpm"))
        if isinstance(tempo, int):
            intent.tempo_bpm = max(40, min(220, tempo))
        length = data.get("length_measures", data.get("bars"))
        if isinstance(length, int):
            intent.bars = length

        instruments = data.get("instrumentation", data.get("instruments"))
        if isinstance(instruments, list) and instruments:
            safe = [str(item)[:40] for item in instruments[:6] if str(item).strip()]
            if safe:
                intent.instruments = safe

        for list_field in ("harmony_plan", "section_plan", "revision_goals"):
            value = data.get(list_field)
            if isinstance(value, list):
                setattr(intent, list_field, value[:16])

        # Re-run dataclass normalization after accepting any live provider fields.
        intent.__post_init__()

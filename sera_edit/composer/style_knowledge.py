"""Versioned, inspectable style knowledge for Sera Composer V0.2."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any


KNOWLEDGE_PATH = Path(__file__).with_name("style_kb") / "style_knowledge.v0.2.json"
REQUIRED_WEIGHT_KEYS = {"safety", "theory", "playability", "motif", "phrase", "style", "preference"}


class StyleKnowledgeError(ValueError):
    """Raised when the local style knowledge file violates its contract."""


class StyleKnowledgeBase:
    """Load, validate, retrieve, and fingerprint project-authored style rules."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = deepcopy(payload)
        self._styles = self._validate(payload)
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.fingerprint = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    @classmethod
    def load(cls, path: str | Path = KNOWLEDGE_PATH) -> "StyleKnowledgeBase":
        """Load a UTF-8 JSON knowledge base from disk."""

        source = Path(path)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StyleKnowledgeError(f"无法读取风格知识库：{source}") from exc
        if not isinstance(payload, dict):
            raise StyleKnowledgeError("风格知识库根节点必须是 JSON object。")
        return cls(payload)

    @property
    def schema_version(self) -> str:
        return str(self._payload["schema_version"])

    @property
    def knowledge_base_id(self) -> str:
        return str(self._payload["knowledge_base_id"])

    @property
    def style_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._styles))

    def profile(self, style_id: str) -> dict[str, Any]:
        """Return one immutable-by-copy style profile."""

        resolved = style_id if style_id in self._styles else "classical"
        return deepcopy(self._styles[resolved])

    def resolve_style(self, brief: str, fallback: str = "classical") -> str:
        """Resolve explicit Chinese or English aliases without broad guessing."""

        text = brief.casefold()
        matches: list[tuple[int, str]] = []
        for style_id, profile in self._styles.items():
            aliases = [style_id, *profile.get("aliases", [])]
            for alias in aliases:
                token = str(alias).casefold().strip()
                if token and token in text:
                    matches.append((len(token), style_id))
        if not matches:
            return fallback if fallback in self._styles else "classical"
        matches.sort(key=lambda item: (-item[0], item[1]))
        return matches[0][1]

    def retrieve(self, brief: str, style_id: str, mode: str, *, limit: int = 5) -> dict[str, Any]:
        """Return a traceable style profile plus brief-relevant rules."""

        profile = self.profile(style_id)
        tokens = set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{1,5}", brief.casefold()))
        ranked: list[tuple[int, str, dict[str, Any], list[str]]] = []
        for rule in profile.get("rules", []):
            if mode not in rule.get("modes", []):
                continue
            matches = sorted(
                token
                for token in tokens
                if any(token in str(tag).casefold() or str(tag).casefold() in token for tag in rule.get("tags", []))
            )
            score = len(matches) * 2 + int(any(token in brief.casefold() for token in profile.get("aliases", [])))
            ranked.append((score, str(rule.get("rule_id", "")), rule, matches))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        matched_rules = []
        for _, _, rule, matches in ranked[: max(1, limit)]:
            item = deepcopy(rule)
            item["match_reason"] = ", ".join(matches) if matches else f"{style_id} core rule"
            item["provenance"] = "sera_original_style_knowledge_v02"
            matched_rules.append(item)
        return {
            "knowledge_base_id": self.knowledge_base_id,
            "schema_version": self.schema_version,
            "fingerprint": self.fingerprint,
            "style_id": profile["style_id"],
            "display_name_zh": profile["display_name_zh"],
            "profile": profile,
            "matched_rules": matched_rules,
            "provenance": deepcopy(self._payload["provenance"]),
        }

    @staticmethod
    def _validate(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        if payload.get("schema_version") != "0.2.0":
            raise StyleKnowledgeError("风格知识库 schema_version 必须为 0.2.0。")
        if not str(payload.get("knowledge_base_id", "")).strip():
            raise StyleKnowledgeError("风格知识库缺少 knowledge_base_id。")
        if not isinstance(payload.get("provenance"), dict):
            raise StyleKnowledgeError("风格知识库缺少 provenance。")
        raw_styles = payload.get("styles")
        if not isinstance(raw_styles, list) or not raw_styles:
            raise StyleKnowledgeError("风格知识库至少需要一个 style profile。")
        styles: dict[str, dict[str, Any]] = {}
        rule_ids: set[str] = set()
        for profile in raw_styles:
            if not isinstance(profile, dict):
                raise StyleKnowledgeError("style profile 必须是 object。")
            style_id = str(profile.get("style_id", ""))
            if not re.fullmatch(r"[a-z][a-z0-9_]*", style_id):
                raise StyleKnowledgeError(f"非法 style_id：{style_id or '<empty>'}")
            if style_id in styles:
                raise StyleKnowledgeError(f"重复 style_id：{style_id}")
            planning = profile.get("planning")
            melody = profile.get("melody")
            weights = profile.get("critic_weights")
            if not isinstance(planning, dict) or not planning.get("progressions"):
                raise StyleKnowledgeError(f"{style_id} 缺少 planning.progressions。")
            if not isinstance(melody, dict) or not melody.get("step_ratio_target"):
                raise StyleKnowledgeError(f"{style_id} 缺少 melody 约束。")
            if not isinstance(weights, dict) or set(weights) != REQUIRED_WEIGHT_KEYS:
                raise StyleKnowledgeError(f"{style_id} critic_weights 字段不完整。")
            total = sum(float(value) for value in weights.values())
            if abs(total - 1.0) > 1e-6 or any(float(value) < 0 for value in weights.values()):
                raise StyleKnowledgeError(f"{style_id} critic_weights 必须非负且总和为 1。")
            for rule in profile.get("rules", []):
                rule_id = str(rule.get("rule_id", "")) if isinstance(rule, dict) else ""
                if not rule_id or rule_id in rule_ids:
                    raise StyleKnowledgeError(f"重复或缺失 rule_id：{rule_id or '<empty>'}")
                rule_ids.add(rule_id)
            styles[style_id] = deepcopy(profile)
        if "classical" not in styles:
            raise StyleKnowledgeError("风格知识库必须提供 classical 安全回退。")
        return styles


@lru_cache(maxsize=1)
def default_style_knowledge_base() -> StyleKnowledgeBase:
    """Return the process-wide immutable default knowledge base."""

    return StyleKnowledgeBase.load()


def retrieve_style_knowledge(
    brief: str,
    style_id: str,
    mode: str,
    *,
    limit: int = 12,
    score_document: dict[str, Any] | None = None,
    target_scope: dict[str, Any] | None = None,
    token_budget: int = 1800,
) -> dict[str, Any]:
    """Return a legacy style profile plus a compact V0.3 atomic-rule context.

    The V0.2 profile remains the deterministic realization/critic parameter
    layer.  Only the small set selected by the V0.3 retriever is exposed as
    ``matched_rules`` and may enter an LLM prompt.
    """

    from sera_edit.composer.knowledge_retrieval import retrieve_composer_knowledge

    profiles = default_style_knowledge_base()
    profile = profiles.profile(style_id)
    retrieval = retrieve_composer_knowledge(
        brief,
        str(profile["style_id"]),
        mode,
        score_document=score_document,
        target_scope=target_scope,
        token_budget=token_budget,
        max_cards=limit,
    )
    return {
        **retrieval,
        "style_id": profile["style_id"],
        "display_name_zh": profile["display_name_zh"],
        "profile": profile,
        "profile_schema_version": profiles.schema_version,
        "profile_fingerprint": profiles.fingerprint,
    }

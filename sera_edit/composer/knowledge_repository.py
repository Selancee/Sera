"""Local, append-only knowledge repository for Composer V0.4."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


REGISTRY_PATH = Path(__file__).with_name("style_kb") / "knowledge_registry.v0.4.json"
RULE_ID_PATTERN = re.compile(r"^[A-Z0-9_-]+$")
ALLOWED_MODES = {"theory_variation", "reharmonize", "orchestration_advice"}
REQUIRED_FIELDS = {
    "rule_id",
    "domain",
    "title_zh",
    "action_zh",
    "avoid_zh",
    "styles",
    "modes",
    "instruments",
    "goals",
    "meters",
    "tags",
    "priority",
    "hard_constraint",
    "provenance",
}


class ComposerKnowledgeError(ValueError):
    """Raised when a registry or atomic rule card violates the V0.4 contract."""


class ComposerKnowledgeRepository:
    """Load versioned JSONL packs and expose immutable cards and index facts."""

    def __init__(self, registry_path: str | Path = REGISTRY_PATH) -> None:
        self.registry_path = Path(registry_path)
        self._registry = self._read_registry()
        self._cards, self._pack_counts = self._read_packs()
        canonical = json.dumps(
            {"registry": self._registry, "cards": self._cards},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        self.fingerprint = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
        self.document_frequencies = self._document_frequencies(self._cards)

    @property
    def schema_version(self) -> str:
        return str(self._registry["schema_version"])

    @property
    def knowledge_base_id(self) -> str:
        return str(self._registry["knowledge_base_id"])

    @property
    def default_token_budget(self) -> int:
        return int(self._registry["default_token_budget"])

    @property
    def default_max_cards(self) -> int:
        return int(self._registry["default_max_cards"])

    @property
    def cards(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(card) for card in self._cards)

    @property
    def provenance(self) -> dict[str, Any]:
        return deepcopy(self._registry["provenance"])

    def status(self) -> dict[str, Any]:
        """Return corpus metadata without returning every rule card."""

        domains = Counter(str(card["domain"]) for card in self._cards)
        styles = Counter(style for card in self._cards for style in card["styles"] if style != "any")
        instruments = Counter(item for card in self._cards for item in card["instruments"] if item != "general")
        return {
            "knowledge_base_id": self.knowledge_base_id,
            "schema_version": self.schema_version,
            "fingerprint": self.fingerprint,
            "total_cards": len(self._cards),
            "pack_count": len(self._pack_counts),
            "pack_counts": dict(sorted(self._pack_counts.items())),
            "domain_counts": dict(sorted(domains.items())),
            "style_counts": dict(sorted(styles.items())),
            "instrument_counts": dict(sorted(instruments.items())),
            "default_token_budget": self.default_token_budget,
            "default_max_cards": self.default_max_cards,
            "provenance": self.provenance,
        }

    def _read_registry(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ComposerKnowledgeError(f"无法读取 Composer 知识库注册表：{self.registry_path}") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != "0.4.0":
            raise ComposerKnowledgeError("Composer 知识库注册表 schema_version 必须为 0.4.0。")
        if not str(payload.get("knowledge_base_id", "")).strip():
            raise ComposerKnowledgeError("Composer 知识库注册表缺少 knowledge_base_id。")
        packs = payload.get("packs")
        if not isinstance(packs, list) or not packs:
            raise ComposerKnowledgeError("Composer 知识库必须声明至少一个 pack。")
        if not isinstance(payload.get("provenance"), dict):
            raise ComposerKnowledgeError("Composer 知识库缺少 provenance。")
        for key in ("default_token_budget", "default_max_cards"):
            if not isinstance(payload.get(key), int) or int(payload[key]) <= 0:
                raise ComposerKnowledgeError(f"Composer 知识库 {key} 必须为正整数。")
        return payload

    def _read_packs(self) -> tuple[list[dict[str, Any]], dict[str, int]]:
        cards: list[dict[str, Any]] = []
        counts: dict[str, int] = {}
        seen: set[str] = set()
        root = self.registry_path.parent.resolve()
        for pack in self._registry["packs"]:
            if not isinstance(pack, dict):
                raise ComposerKnowledgeError("知识 pack 声明必须是 object。")
            pack_id = str(pack.get("pack_id", "")).strip()
            relative = Path(str(pack.get("path", "")))
            source = (root / relative).resolve()
            try:
                source.relative_to(root)
            except ValueError as exc:
                raise ComposerKnowledgeError(f"知识 pack 路径越界：{relative}") from exc
            count = 0
            try:
                lines = source.read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                raise ComposerKnowledgeError(f"无法读取知识 pack：{source}") from exc
            for line_number, raw_line in enumerate(lines, start=1):
                if not raw_line.strip():
                    continue
                try:
                    card = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise ComposerKnowledgeError(f"{source.name}:{line_number} 不是合法 JSON。") from exc
                self._validate_card(card, source.name, line_number)
                rule_id = str(card["rule_id"])
                if rule_id in seen:
                    raise ComposerKnowledgeError(f"重复 rule_id：{rule_id}")
                seen.add(rule_id)
                normalized = deepcopy(card)
                normalized["pack_id"] = pack_id
                cards.append(normalized)
                count += 1
            if not pack_id or count == 0:
                raise ComposerKnowledgeError(f"知识 pack 为空或缺少 pack_id：{relative}")
            counts[pack_id] = count
        return cards, counts

    @staticmethod
    def _validate_card(card: Any, source: str, line_number: int) -> None:
        prefix = f"{source}:{line_number}"
        if not isinstance(card, dict) or set(card) != REQUIRED_FIELDS:
            raise ComposerKnowledgeError(f"{prefix} 字段集合不符合 RuleCard V0.4。")
        rule_id = str(card.get("rule_id", ""))
        if not RULE_ID_PATTERN.fullmatch(rule_id):
            raise ComposerKnowledgeError(f"{prefix} rule_id 非法：{rule_id or '<empty>'}")
        for key in ("domain", "title_zh", "action_zh", "avoid_zh", "provenance"):
            if not str(card.get(key, "")).strip():
                raise ComposerKnowledgeError(f"{prefix} {key} 不能为空。")
        for key in ("styles", "modes", "instruments", "meters", "tags"):
            value = card.get(key)
            if not isinstance(value, list) or not value or any(not str(item).strip() for item in value):
                raise ComposerKnowledgeError(f"{prefix} {key} 必须是非空字符串数组。")
        if not isinstance(card.get("goals"), list):
            raise ComposerKnowledgeError(f"{prefix} goals 必须是数组。")
        if not set(card["modes"]).issubset(ALLOWED_MODES):
            raise ComposerKnowledgeError(f"{prefix} 包含不支持的 mode。")
        if not isinstance(card.get("priority"), (int, float)) or not 0 <= float(card["priority"]) <= 1:
            raise ComposerKnowledgeError(f"{prefix} priority 必须在 0 到 1。")
        if not isinstance(card.get("hard_constraint"), bool):
            raise ComposerKnowledgeError(f"{prefix} hard_constraint 必须为 boolean。")
        if card.get("provenance") not in {
            "sera_original_engineering_summary_v03",
            "sera_original_research_summary_v04",
        }:
            raise ComposerKnowledgeError(f"{prefix} provenance 不允许使用未审核来源。")

    @staticmethod
    def _document_frequencies(cards: Iterable[dict[str, Any]]) -> dict[str, int]:
        frequencies: Counter[str] = Counter()
        for card in cards:
            frequencies.update(set(card_tokens(card)))
        return dict(frequencies)


def card_tokens(card: dict[str, Any]) -> set[str]:
    """Return retrieval tokens for one card."""

    values: list[str] = [
        str(card.get("domain", "")),
        str(card.get("title_zh", "")),
        str(card.get("action_zh", "")),
        str(card.get("avoid_zh", "")),
    ]
    for key in ("styles", "modes", "instruments", "goals", "meters", "tags"):
        values.extend(str(item) for item in card.get(key, []))
    return lexical_tokens(" ".join(values))


def lexical_tokens(text: str) -> set[str]:
    """Tokenize Latin words and short CJK n-grams without external models."""

    normalized = text.casefold()
    tokens = set(re.findall(r"[a-z0-9][a-z0-9_/-]*", normalized))
    for run in re.findall(r"[\u4e00-\u9fff]+", normalized):
        if len(run) <= 4:
            tokens.add(run)
        for width in (2, 3, 4):
            tokens.update(run[index : index + width] for index in range(max(0, len(run) - width + 1)))
    return {token for token in tokens if token}


@lru_cache(maxsize=1)
def default_composer_knowledge_repository() -> ComposerKnowledgeRepository:
    """Return the process-wide immutable V0.4 repository."""

    return ComposerKnowledgeRepository()

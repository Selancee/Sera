"""Deterministic large-corpus, small-context retrieval for Composer V0.4."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from copy import deepcopy
from typing import Any

from sera_edit.composer.knowledge_repository import (
    ComposerKnowledgeRepository,
    card_tokens,
    default_composer_knowledge_repository,
    lexical_tokens,
)
from sera_edit.composer.texture_analysis import analyze_texture


GOAL_ALIASES = {
    "cadence": ("cadence", "closure", "终止", "收束", "结尾"),
    "motif": ("motif", "动机", "主题"),
    "phrase": ("phrase", "乐句", "呼吸", "高潮"),
    "harmony": ("harmony", "reharmon", "和声", "和弦"),
    "voice_leading": ("voice leading", "声部进行", "声部连接", "对位"),
    "rhythm": ("rhythm", "groove", "节奏", "律动", "切分"),
    "orchestration": ("orchestrat", "instrument", "配器", "乐器", "音色"),
    "playability": ("playable", "idiomatic", "可演奏", "演奏性", "音域"),
    "tension": ("tension", "climax", "张力", "高潮", "悬念"),
    "lyrical": ("lyrical", "singing", "抒情", "歌唱"),
    "energy": ("energy", "driving", "能量", "推动", "激烈"),
    "dark": ("dark", "暗色", "阴暗"),
    "bright": ("bright", "明亮", "明快"),
    "melodic_expectation": ("expectation", "expectancy", "huron", "休伦", "旋律期待", "旋律预期"),
    "texture": ("texture", "织体", "复调", "主调", "齐奏", "分层"),
    "composition_craft": ("composition", "compositional", "作曲", "写作", "发展手法"),
}

INSTRUMENT_ALIASES = {
    "piano": ("piano", "钢琴"),
    "violin": ("violin", "小提琴"),
    "cello": ("cello", "大提琴"),
    "flute": ("flute", "长笛"),
    "clarinet": ("clarinet", "单簧管"),
    "trumpet": ("trumpet", "小号"),
    "guitar": ("guitar", "吉他"),
    "voice": ("voice", "vocal", "choir", "人声", "合唱"),
}


def retrieve_composer_knowledge(
    brief: str,
    style_id: str,
    mode: str,
    *,
    score_document: dict[str, Any] | None = None,
    target_scope: dict[str, Any] | None = None,
    token_budget: int | None = None,
    max_cards: int | None = None,
    repository: ComposerKnowledgeRepository | None = None,
) -> dict[str, Any]:
    """Retrieve a compact, traceable set of rule cards from the local corpus."""

    repo = repository or default_composer_knowledge_repository()
    budget = max(320, min(int(token_budget or repo.default_token_budget), 6000))
    limit = max(1, min(int(max_cards or repo.default_max_cards), 24))
    query = _query_features(brief, style_id, mode, score_document, target_scope)
    query_tokens = lexical_tokens(" ".join(query["search_terms"]))
    cards = list(repo.cards)
    scored: list[tuple[float, str, dict[str, Any], list[str]]] = []
    total_cards = max(1, len(cards))
    for card in cards:
        if mode not in card["modes"]:
            continue
        tokens = card_tokens(card)
        shared = sorted(query_tokens & tokens)
        lexical = sum(math.log((total_cards + 1) / (repo.document_frequencies.get(token, 0) + 1)) + 1 for token in shared)
        lexical /= max(1.0, math.sqrt(len(tokens)))
        metadata = _metadata_score(card, query)
        scored.append((round(metadata + lexical, 8), str(card["rule_id"]), card, shared))
    scored.sort(key=lambda item: (-item[0], item[1]))

    selected: list[dict[str, Any]] = []
    selected_domains: Counter[str] = Counter()
    selected_instrument_specific = False
    selected_style_specific = False
    selected_goal_specific = False
    used_tokens = 0
    remaining = list(scored)
    while remaining and len(selected) < limit:
        # Keep one broad craft domain from crowding style, harmony, texture, and
        # expectation out of the deliberately small prompt context.
        balanced_remaining = [
            item for item in remaining if selected_domains[str(item[2]["domain"])] < 4
        ] or remaining
        choice = max(
            balanced_remaining,
            key=lambda item: (
                item[0]
                + (0.85 if selected_domains[str(item[2]["domain"])] == 0 else 0.0)
                + (2.4 if not selected_instrument_specific and _instrument_specific(item[2], query) else 0.0)
                + (1.4 if not selected_style_specific and query["style_id"] in item[2]["styles"] else 0.0)
                + (0.9 if not selected_goal_specific and _goal_specific(item[2], query) else 0.0),
                item[0],
                item[1],
            ),
        )
        remaining.remove(choice)
        score, _, card, shared = choice
        compact = _compact_card(card, score, shared, query)
        card_tokens_estimate = estimate_tokens(compact)
        if used_tokens + card_tokens_estimate > budget:
            continue
        selected.append(compact)
        selected_domains[str(card["domain"])] += 1
        selected_instrument_specific = selected_instrument_specific or _instrument_specific(card, query)
        selected_style_specific = selected_style_specific or query["style_id"] in card["styles"]
        selected_goal_specific = selected_goal_specific or _goal_specific(card, query)
        used_tokens += card_tokens_estimate

    query_payload = {key: value for key, value in query.items() if key != "search_terms"}
    query_fingerprint = "sha256:" + hashlib.sha256(
        json.dumps(query_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "knowledge_base_id": repo.knowledge_base_id,
        "schema_version": repo.schema_version,
        "fingerprint": repo.fingerprint,
        "query_fingerprint": query_fingerprint,
        "query": query_payload,
        "matched_rules": selected,
        "selected_rule_ids": [card["rule_id"] for card in selected],
        "retrieval": {
            "strategy": "metadata_lexical_idf_domain_diversity_cap4_v2",
            "total_cards": len(cards),
            "pack_count": repo.status()["pack_count"],
            "eligible_cards": len(scored),
            "selected_cards": len(selected),
            "dropped_cards": max(0, len(scored) - len(selected)),
            "estimated_tokens": used_tokens,
            "token_budget": budget,
            "max_cards": limit,
            "selected_domains": dict(sorted(selected_domains.items())),
            "full_corpus_sent_to_llm": False,
        },
        "provenance": repo.provenance,
    }


def estimate_tokens(payload: dict[str, Any]) -> int:
    """Use a deterministic UTF-8 size estimate suitable for hard prompt budgeting."""

    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return max(1, math.ceil(len(serialized.encode("utf-8")) / 4) + 4)


def _query_features(
    brief: str,
    style_id: str,
    mode: str,
    score_document: dict[str, Any] | None,
    target_scope: dict[str, Any] | None,
) -> dict[str, Any]:
    text = brief.casefold()
    global_data = (score_document or {}).get("global") or {}
    key = str(global_data.get("key") or "unknown")
    meter = str(global_data.get("meter") or "unknown")
    instruments: set[str] = set()
    for track in (score_document or {}).get("tracks") or []:
        raw = str(track.get("instrument") or "").casefold()
        resolved = _resolve_instrument(raw)
        if resolved:
            instruments.add(resolved)
    for canonical, aliases in INSTRUMENT_ALIASES.items():
        if any(alias in text for alias in aliases):
            instruments.add(canonical)
    if not instruments:
        instruments.add("general")
    goals = sorted(goal for goal, aliases in GOAL_ALIASES.items() if any(alias in text for alias in aliases))
    if not goals:
        goals = ["harmony" if mode == "reharmonize" else "orchestration" if mode == "orchestration_advice" else "motif"]
    essential_goals = {"texture", "composition_craft"}
    if mode == "theory_variation":
        essential_goals.add("melodic_expectation")
    goals = sorted(set(goals) | essential_goals)
    texture = (
        analyze_texture(score_document, target_scope or {}).get("texture", "unknown")
        if score_document and target_scope
        else "unknown"
    )
    measures = sorted(
        {
            int(value)
            for value in (target_scope or {}).get("measures") or []
            if isinstance(value, int) or (isinstance(value, str) and value.isdigit())
        }
    )
    terms = [brief, style_id, mode, key, meter, texture, *instruments, *goals]
    return {
        "style_id": style_id,
        "mode": mode,
        "key": key,
        "meter": meter,
        "instruments": sorted(instruments),
        "goals": goals,
        "source_texture": texture,
        "target_measures": measures,
        "search_terms": terms,
    }


def _resolve_instrument(raw: str) -> str | None:
    for canonical, aliases in INSTRUMENT_ALIASES.items():
        if canonical == raw or any(alias in raw for alias in aliases):
            return canonical
    return "general" if raw else None


def _metadata_score(card: dict[str, Any], query: dict[str, Any]) -> float:
    score = float(card["priority"])
    styles = set(str(item) for item in card["styles"])
    instruments = set(str(item) for item in card["instruments"])
    goals = set(str(item).casefold() for item in card["goals"] + card["tags"])
    score += 4.0 if query["style_id"] in styles else 0.7 if "any" in styles else -2.0
    query_instruments = set(query["instruments"])
    score += 4.2 if instruments & query_instruments else 0.8 if "general" in instruments else -2.8
    score += 1.4 * len(goals & set(query["goals"]))
    essential_domain_goals = {
        "melodic_expectation": "melodic_expectation",
        "texture": "texture",
        "composition_craft": "composition_craft",
    }
    domain = str(card.get("domain") or "")
    if essential_domain_goals.get(domain) in set(query["goals"]):
        score += 4.2
    score += 1.1 if str(query.get("source_texture")) in goals else 0.0
    score += 0.8 if query["meter"] in card["meters"] else 0.25 if "any" in card["meters"] else 0.0
    if bool(card["hard_constraint"]):
        score += 0.3
    return score


def _instrument_specific(card: dict[str, Any], query: dict[str, Any]) -> bool:
    return bool((set(card["instruments"]) - {"general"}) & set(query["instruments"]))


def _goal_specific(card: dict[str, Any], query: dict[str, Any]) -> bool:
    return bool(set(query["goals"]) & set(card["goals"] + card["tags"]))


def _compact_card(card: dict[str, Any], score: float, shared: list[str], query: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if query["style_id"] in card["styles"]:
        reasons.append(f"style:{query['style_id']}")
    matched_instruments = sorted(set(query["instruments"]) & set(card["instruments"]))
    if matched_instruments:
        reasons.append("instrument:" + ",".join(matched_instruments))
    matched_goals = sorted(set(query["goals"]) & set(card["goals"] + card["tags"]))
    if matched_goals:
        reasons.append("goal:" + ",".join(matched_goals))
    if query.get("source_texture") in set(card["goals"] + card["tags"]):
        reasons.append(f"texture:{query['source_texture']}")
    if shared:
        reasons.append("terms:" + ",".join(shared[:4]))
    if not reasons:
        reasons.append(f"domain:{card['domain']}")
    return {
        "rule_id": card["rule_id"],
        "domain": card["domain"],
        "title_zh": card["title_zh"],
        "action_zh": card["action_zh"],
        "avoid_zh": card["avoid_zh"],
        "hard_constraint": card["hard_constraint"],
        "relevance_score": round(score, 4),
        "match_reason": "; ".join(reasons),
        "provenance": card["provenance"],
    }

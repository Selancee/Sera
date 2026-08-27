"""Composer V0.4 large-corpus, small-context regressions."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from sera_edit.composer.knowledge_repository import (
    ComposerKnowledgeError,
    ComposerKnowledgeRepository,
    REGISTRY_PATH,
    default_composer_knowledge_repository,
)
from sera_edit.composer.knowledge_retrieval import retrieve_composer_knowledge
from sera_edit.composer.planner import plan_composition
from sera_edit.providers.base import ProviderResponse


def test_repository_is_large_versioned_unique_and_traceable() -> None:
    repository = default_composer_knowledge_repository()
    status = repository.status()
    rule_ids = [card["rule_id"] for card in repository.cards]
    assert status["schema_version"] == "0.4.0"
    assert status["total_cards"] == 358
    assert status["pack_count"] == 7
    assert status["pack_counts"]["melodic_expectation"] == 24
    assert status["pack_counts"]["texture_structure"] == 28
    assert status["pack_counts"]["composition_craft"] == 40
    assert len(rule_ids) == len(set(rule_ids))
    assert status["fingerprint"].startswith("sha256:")
    assert "copied" in status["provenance"]["content_policy"].lower()


def test_repository_rejects_duplicate_rule_ids(tmp_path) -> None:
    source_registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    pack_root = tmp_path / "packs"
    pack_root.mkdir()
    source_card = default_composer_knowledge_repository().cards[0]
    source_card.pop("pack_id")
    duplicate_lines = "\n".join(json.dumps(source_card, ensure_ascii=False) for _ in range(2)) + "\n"
    (pack_root / "duplicate.jsonl").write_text(duplicate_lines, encoding="utf-8")
    source_registry["packs"] = [{"pack_id": "duplicate", "path": "packs/duplicate.jsonl"}]
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps(source_registry, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ComposerKnowledgeError, match="重复 rule_id"):
        ComposerKnowledgeRepository(registry)


def test_retrieval_is_score_style_instrument_and_goal_specific(two_staff_score: dict) -> None:
    classical = retrieve_composer_knowledge(
        "为钢琴写古典变奏，保持动机并形成清晰终止",
        "classical",
        "theory_variation",
        score_document=two_staff_score,
        target_scope={"measures": [1, 2]},
    )
    jazz = retrieve_composer_knowledge(
        "为小号重新配置爵士和声，使用平滑导向音",
        "jazz",
        "reharmonize",
        score_document={"global": {"key": "F major", "meter": "4/4"}, "tracks": [{"instrument": "trumpet"}]},
        target_scope={"measures": [5, 6]},
    )
    classical_ids = classical["selected_rule_ids"]
    jazz_ids = jazz["selected_rule_ids"]
    assert any("STYLE-CLASSICAL" in rule_id for rule_id in classical_ids)
    assert any("INST-PIANO" in rule_id for rule_id in classical_ids)
    assert any("STYLE-JAZZ" in rule_id for rule_id in jazz_ids)
    assert any("INST-TRUMPET" in rule_id for rule_id in jazz_ids)
    assert classical_ids != jazz_ids
    assert classical["query"]["key"] == two_staff_score["global"]["key"]
    assert jazz["query"]["target_measures"] == [5, 6]


def test_retrieval_is_deterministic_and_never_exceeds_context_budget(two_staff_score: dict) -> None:
    kwargs = {
        "brief": "写一个极简主义钢琴动机，逐步增加张力",
        "style_id": "minimal",
        "mode": "theory_variation",
        "score_document": two_staff_score,
        "target_scope": {"measures": [1, 2]},
        "token_budget": 520,
        "max_cards": 24,
    }
    first = retrieve_composer_knowledge(**kwargs)
    second = retrieve_composer_knowledge(**kwargs)
    assert first["matched_rules"] == second["matched_rules"]
    assert first["query_fingerprint"] == second["query_fingerprint"]
    assert 1 <= first["retrieval"]["selected_cards"] < first["retrieval"]["total_cards"]
    assert first["retrieval"]["estimated_tokens"] <= 520
    assert first["retrieval"]["full_corpus_sent_to_llm"] is False


class _CapturingProvider:
    provider = "test"
    model = "capture"

    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def generate(self, messages: list[dict[str, str]], **_: object) -> ProviderResponse:
        self.messages = deepcopy(messages)
        parsed = {
            "mode": "theory_variation",
            "style_family": "classical",
            "harmonic_progression": ["I", "V", "I"],
            "texture": "melody_accompaniment",
            "motif_strategy": "preserve_contour",
            "tension_curve": [0.2, 0.7, 0.2],
            "dynamics_curve": ["mp", "mf", "mp"],
            "preserve_melody": False,
            "orchestration_notes": [],
        }
        return ProviderResponse(raw_text=json.dumps(parsed), parsed_output=parsed, provider=self.provider, model=self.model, latency_ms=1)


def test_planner_prompt_contains_only_retrieved_cards_not_full_repository(two_staff_score: dict) -> None:
    provider = _CapturingProvider()
    plan, _, evidence = plan_composition(
        two_staff_score,
        "为钢琴写一个古典动机变奏并清晰收束",
        {"measures": [1, 2]},
        {},
        provider=provider,
    )
    payload = json.loads(provider.messages[1]["content"])
    context = payload["retrieved_knowledge_context"]
    assert 1 <= len(context["selected_rules"]) <= 12
    assert len(context["selected_rules"]) == context["retrieval"]["selected_cards"]
    assert context["retrieval"]["total_cards"] == 358
    assert context["retrieval"]["full_corpus_sent_to_llm"] is False
    assert "profile" not in payload["retrieved_knowledge_context"]
    assert "planning" not in payload["retrieved_knowledge_context"]
    assert plan.style_rule_ids == tuple(card["rule_id"] for card in context["selected_rules"])
    assert plan.knowledge_token_estimate <= context["retrieval"]["token_budget"]
    assert evidence["prompt_version"] == "sera_composition_plan_v4.1"
    assert payload["source_texture_analysis"]["texture"] in {
        "monophonic",
        "homorhythmic_chordal",
        "melody_accompaniment",
        "contrapuntal",
        "layered",
    }


def test_retrieval_includes_expectation_texture_and_composition_craft(two_staff_score: dict) -> None:
    result = retrieve_composer_knowledge(
        "依据休伦的旋律期待改写钢琴乐句，并识别和保留原有织体",
        "classical",
        "theory_variation",
        score_document=two_staff_score,
        target_scope={"measures": [1, 2]},
    )
    selected_domains = {item["domain"] for item in result["matched_rules"]}
    assert {"melodic_expectation", "texture", "composition_craft"}.issubset(selected_domains)
    assert result["query"]["source_texture"] == "homorhythmic_chordal"
    assert result["retrieval"]["selected_cards"] <= 12
    assert result["retrieval"]["estimated_tokens"] <= 1800


def test_retrieval_does_not_mutate_score(two_staff_score: dict) -> None:
    before = json.dumps(two_staff_score, sort_keys=True)
    retrieve_composer_knowledge(
        "浪漫主义钢琴乐句",
        "romantic",
        "theory_variation",
        score_document=two_staff_score,
        target_scope={"measures": [1]},
    )
    assert json.dumps(two_staff_score, sort_keys=True) == before


def test_style_knowledge_api_reports_corpus_without_dumping_cards() -> None:
    response = TestClient(app).get("/sera-edit/composer/style-knowledge")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "0.4.0"
    assert payload["total_cards"] == 358
    assert payload["pack_count"] == 7
    assert payload["default_token_budget"] == 1800
    assert "cards" not in payload

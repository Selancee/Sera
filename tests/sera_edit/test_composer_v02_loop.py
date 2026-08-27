from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from sera_edit.composer.phrase_analysis import analyze_phrase
from sera_edit.composer.pipeline import generate_composition_candidates
from sera_edit.composer.preference import ComposerPreferenceStore
from sera_edit.composer.style_knowledge import (
    KNOWLEDGE_PATH,
    StyleKnowledgeBase,
    StyleKnowledgeError,
    default_style_knowledge_base,
)


def test_style_knowledge_is_versioned_traceable_and_weight_normalized() -> None:
    knowledge = default_style_knowledge_base()
    assert knowledge.schema_version == "0.2.0"
    assert set(knowledge.style_ids) == {"classical", "romantic", "jazz", "pop", "minimal", "modal", "cinematic"}
    romantic = knowledge.retrieve("写一个浪漫主义高潮乐句", "romantic", "theory_variation")
    assert romantic["fingerprint"].startswith("sha256:")
    assert romantic["matched_rules"]
    assert all(item["provenance"] == "sera_original_style_knowledge_v02" for item in romantic["matched_rules"])
    assert sum(romantic["profile"]["critic_weights"].values()) == pytest.approx(1.0)
    assert "copied" in romantic["provenance"]["content_policy"].lower()


def test_style_knowledge_rejects_duplicate_style_ids() -> None:
    payload = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    payload["styles"].append(dict(payload["styles"][0]))
    with pytest.raises(StyleKnowledgeError, match="重复 style_id"):
        StyleKnowledgeBase(payload)


def test_phrase_analysis_extracts_primary_motif_without_mutation(two_staff_score: dict) -> None:
    before = json.dumps(two_staff_score, sort_keys=True)
    analysis = analyze_phrase(two_staff_score, {"measures": [1, 2]})
    assert analysis["analysis_version"] == "0.2.0"
    assert analysis["primary_voice_id"] == "right_hand:v1"
    assert analysis["source_motif"]["intervals"][:3] == [2, 2, 1]
    assert analysis["source_motif"]["contour"] == "ascending"
    assert analysis["fingerprint"].startswith("sha256:")
    assert json.dumps(two_staff_score, sort_keys=True) == before


def test_v02_pipeline_searches_wide_and_returns_ranked_diverse_candidates(two_staff_score: dict) -> None:
    result = generate_composition_candidates(
        two_staff_score,
        "创作浪漫主义旋律变化，形成长线条和清晰终止",
        {"measures": [1, 2]},
        {},
        candidate_count=3,
        search_width=16,
    )
    assert result["status"] == "generated"
    assert result["style_knowledge"]["schema_version"] == "0.4.0"
    assert result["style_knowledge"]["profile_schema_version"] == "0.2.0"
    assert result["style_knowledge"]["retrieval"]["full_corpus_sent_to_llm"] is False
    assert result["phrase_analysis"]["primary_voice_id"] == "right_hand:v1"
    assert result["search_summary"]["search_width"] == 16
    assert result["search_summary"]["evaluated"] >= 3
    assert result["search_summary"]["returned"] == 3
    assert result["comparison_id"].startswith("comparison_")
    assert result["selected_candidate_id"] == result["candidates"][0]["candidate_id"]
    for candidate in result["candidates"]:
        review = candidate["review"]
        assert review["reviewer"] == "sera_deterministic_critics_v3"
        assert 0 <= review["motif_score"] <= 1
        assert 0 <= review["phrase_score"] <= 1
        assert 0 <= review["style_score"] <= 1
        assert all(operation["type"] == "set_pitch" for operation in candidate["patch"]["operations"])


@pytest.mark.parametrize(
    ("brief", "style_id"),
    [
        ("创作古典风格旋律变化", "classical"),
        ("创作浪漫主义旋律变化", "romantic"),
        ("创作爵士旋律变化", "jazz"),
        ("创作流行旋律变化", "pop"),
        ("创作极简旋律变化", "minimal"),
        ("创作调式旋律变化", "modal"),
        ("创作电影配乐式旋律变化", "cinematic"),
    ],
)
def test_all_v02_style_profiles_generate_safe_candidate_sets(two_staff_score: dict, brief: str, style_id: str) -> None:
    result = generate_composition_candidates(
        two_staff_score,
        brief,
        {"measures": [1, 2]},
        {},
        candidate_count=3,
        search_width=16,
    )
    assert result["status"] == "generated"
    assert result["style_knowledge"]["style_id"] == style_id
    assert len(result["candidates"]) == 3
    assert all(candidate["preview"]["validation_report"]["status"] == "valid" for candidate in result["candidates"])
    assert all(candidate["review"]["safety_score"] == 1.0 for candidate in result["candidates"])


def test_local_preference_store_is_idempotent_and_contains_no_score_data(tmp_path) -> None:
    store = ComposerPreferenceStore(tmp_path / "preferences.jsonl")
    request = {
        "comparison_id": "comparison_test",
        "plan_id": "plan_test",
        "style_family": "romantic",
        "selected_candidate_id": "candidate_2",
        "rejected_candidate_ids": ["candidate_1", "candidate_3"],
        "selected_review": {
            "motif_score": 0.9,
            "phrase_score": 0.8,
            "style_score": 0.85,
            "theory_score": 0.75,
            "playability_score": 1.0,
        },
        "reasons": ["motif", "phrase"],
    }
    first = store.record(**request)
    second = store.record(**request)
    assert first["recorded"] is True
    assert second["recorded"] is False
    profile = store.profile()
    assert profile["feedback_count"] == 1
    assert profile["reason_counts"]["motif"] == 1
    assert profile["dimension_targets"]["phrase"] == 0.8
    saved = (tmp_path / "preferences.jsonl").read_text(encoding="utf-8")
    assert "score_document" not in saved
    assert "pitch" not in saved
    assert '"stores_score_content": false' in saved


def test_preference_profile_changes_candidate_scoring_without_changing_safety(two_staff_score: dict) -> None:
    profile = {
        "schema_version": "0.2.0",
        "feedback_count": 9,
        "dimension_targets": {"motif": 0.95, "phrase": 0.9, "style": 0.9},
        "reason_counts": {"motif": 4, "phrase": 3, "style": 2},
        "active": True,
    }
    result = generate_composition_candidates(
        two_staff_score,
        "创作有清晰动机和乐句高潮的古典变化",
        {"measures": [1, 2]},
        {},
        candidate_count=2,
        preference_profile=profile,
    )
    assert result["status"] == "generated"
    assert result["preference_profile"]["feedback_count"] == 9
    assert all(candidate["review"]["critic_weights"]["preference"] > 0.05 for candidate in result["candidates"])
    assert all(candidate["review"]["safety_score"] == 1.0 for candidate in result["candidates"])


def test_composer_feedback_api_updates_local_profile(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    feedback_path = tmp_path / "api_preferences.jsonl"
    monkeypatch.setenv("SERA_COMPOSER_FEEDBACK_FILE", str(feedback_path))
    response = TestClient(app).post(
        "/sera-edit/composer/feedback",
        json={
            "comparison_id": "comparison_api",
            "plan_id": "plan_api",
            "style_family": "classical",
            "selected_candidate_id": "candidate_1",
            "rejected_candidate_ids": ["candidate_2"],
            "selected_review": {"motif_score": 0.8, "phrase_score": 0.7, "style_score": 0.9},
            "reasons": ["style"],
        },
    )
    assert response.status_code == 200
    assert response.json()["recorded"] is True
    profile = TestClient(app).get("/sera-edit/composer/preference-profile")
    assert profile.status_code == 200
    assert profile.json()["feedback_count"] == 1
    knowledge = TestClient(app).get("/sera-edit/composer/style-knowledge")
    assert knowledge.status_code == 200
    assert knowledge.json()["schema_version"] == "0.4.0"
    assert knowledge.json()["profile_schema_version"] == "0.2.0"
    assert knowledge.json()["total_cards"] >= 200

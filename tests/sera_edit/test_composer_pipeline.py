"""Composer V0.1 planning, ranking, and host-preservation regressions."""

from __future__ import annotations

import copy
import json
import threading
import time

from fastapi.testclient import TestClient

from backend.app import app
from backend.services.musicxml_source_patch_service import patch_musicxml_preserving_source
from backend.services.score_document_service import (
    musicxml_to_score_document,
    new_score_document,
    normalize_score_document,
    score_document_to_musicxml,
)
from sera_edit.composer.pipeline import generate_composition_candidates
from sera_edit.composer.pipeline import (
    compose_responsive_with_runtime,
    compose_with_runtime,
    composer_llm_max_output_tokens,
    composer_llm_timeout_seconds,
)
from sera_edit.composer.refinement import default_composer_refinement_store
from sera_edit.composer.planner import infer_mode_and_style, plan_composition
from sera_edit.composer.theory_knowledge import retrieve_theory
from sera_edit.providers.base import ProviderResponse
from sera_edit.providers.runtime import LLMRuntimeSettings


class _PlanningProvider:
    provider = "test"
    model = "planning-test"

    def generate(self, messages: list[dict[str, str]], *_: object, **__: object) -> ProviderResponse:
        self.messages = messages
        return ProviderResponse(
            raw_text="{}",
            parsed_output={
                "mode": "reharmonize",
                "style_family": "romantic",
                "harmonic_progression": ["I", "vi"],
                "texture": "arpeggiated",
                "motif_strategy": "sequence",
                "tension_curve": [0.2, 0.8],
                "dynamics_curve": ["mp", "f"],
                "preserve_melody": True,
                "orchestration_notes": ["Keep the melody clear."],
            },
            provider=self.provider,
            model=self.model,
            latency_ms=12.0,
            input_tokens=120,
            output_tokens=80,
            request_id="composer_plan_test",
        )


class _BlockingPlanningProvider(_PlanningProvider):
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.max_tokens: int | None = None

    def generate(self, *args: object, **kwargs: object) -> ProviderResponse:
        self.max_tokens = int(kwargs.get("max_tokens") or 0)
        self.started.set()
        if not self.release.wait(timeout=10):
            raise RuntimeError("test provider was not released")
        messages = args[0] if args else []
        return super().generate(messages, **kwargs)


def test_theory_retrieval_is_traceable_and_mode_bounded() -> None:
    context = retrieve_theory("为钢琴做浪漫主义和声变化", "reharmonize", "romantic")
    assert context
    assert context[0]["claim_id"]
    assert all(item["provenance"] == "sera_curated_theory_summary" for item in context)
    assert all("reharmonize" in item["applies_to"] for item in context)


def test_voice_count_phrase_is_not_misrouted_as_harmony() -> None:
    melody_mode, _ = infer_mode_and_style("重写旋律，保持节奏和声部数量不变")
    harmony_mode, _ = infer_mode_and_style("改写和声进行并保留旋律")

    assert melody_mode == "theory_variation"
    assert harmony_mode == "reharmonize"


def test_llm_plan_cannot_change_source_facts_or_baseline(two_staff_score: dict) -> None:
    plan, _, evidence = plan_composition(
        two_staff_score,
        "Reharmonize this passage in a romantic style.",
        {"measures": [1, 2]},
        {"staffs": [1]},
        provider=_PlanningProvider(),
    )
    assert plan.mode == "reharmonize"
    assert plan.key == two_staff_score["global"]["key"]
    assert plan.meter == two_staff_score["global"]["meter"]
    assert plan.measures == (1, 2)
    assert plan.preserve_rhythm is True
    assert plan.preserve_event_count is True
    assert plan.preserve_instrumentation is True
    assert evidence["planner"] == "live_llm"


def test_composer_planner_sends_summary_not_event_level_score_context(two_staff_score: dict) -> None:
    provider = _PlanningProvider()

    plan_composition(
        two_staff_score,
        "创作一个有清晰终止的古典变化",
        {"measures": [1, 2]},
        {},
        provider=provider,
        max_tokens=2048,
    )

    payload = json.loads(provider.messages[1]["content"])
    summary = payload["immutable_score_context"]
    assert summary["selected_note_count"] == 16
    assert summary["voice_count"] == 2
    assert "events" not in summary
    assert "event_id" not in provider.messages[1]["content"]


def test_composer_returns_ranked_transaction_valid_candidates(two_staff_score: dict) -> None:
    result = generate_composition_candidates(
        two_staff_score,
        "创作一个有清晰终止的古典风格变化，保留节奏",
        {"measures": [1, 2]},
        {},
        candidate_count=3,
    )
    assert result["status"] == "generated"
    assert len(result["candidates"]) == 3
    assert result["selected_candidate_id"] == result["candidates"][0]["candidate_id"]
    assert result["baseline_guarantees"]["preserve_host_layout"] is True
    scores = [candidate["review"]["overall_score"] for candidate in result["candidates"]]
    assert scores == sorted(scores, reverse=True)
    for candidate in result["candidates"]:
        assert candidate["preview"]["validation_report"]["status"] == "valid"
        assert candidate["review"]["status"] == "valid"
        assert candidate["preview"]["diff"]["added"] == []
        assert candidate["preview"]["diff"]["deleted"] == []
        assert all(item["changed_fields"] == ["pitch"] for item in candidate["preview"]["diff"]["changed"])


def test_reharmonization_preserves_protected_melody(two_staff_score: dict) -> None:
    result = generate_composition_candidates(
        two_staff_score,
        "重新设计浪漫主义和声，右手旋律必须保持不变",
        {"measures": [1, 2]},
        {"staffs": [1]},
        candidate_count=2,
        provider=_PlanningProvider(),
    )
    assert result["status"] == "generated"
    for candidate in result["candidates"]:
        changed = candidate["preview"]["diff"]["changed"]
        assert changed
        assert all(item["before_location"]["staff"] == "left_hand" for item in changed)


def test_composer_search_skips_protected_part_of_a_broader_target(two_staff_score: dict) -> None:
    result = generate_composition_candidates(
        two_staff_score,
        "创作古典风格旋律变化，并保持左手不变",
        {"measures": [1, 2]},
        {"staffs": [2]},
        candidate_count=2,
    )

    assert result["status"] == "generated"
    assert result["failure_analysis"] is None
    for candidate in result["candidates"]:
        changed = candidate["preview"]["diff"]["changed"]
        assert changed
        assert all(item["before_location"]["staff"] == "right_hand" for item in changed)


def test_composer_explains_when_target_is_fully_protected(two_staff_score: dict) -> None:
    result = generate_composition_candidates(
        two_staff_score,
        "创作旋律变化",
        {"measures": [1, 2], "staffs": [1]},
        {"staffs": [1]},
        candidate_count=2,
    )

    assert result["status"] == "unsupported"
    assert result["candidates"] == []
    assert result["failure_analysis"]["code"] == "target_fully_protected"
    assert result["failure_analysis"]["counts"]["target_notes"] == 8
    assert result["failure_analysis"]["counts"]["protected_target_notes"] == 8
    assert "全部位于保护范围" in result["reason"]


def test_reharmonization_does_not_rewrite_a_single_preserved_melody(two_staff_score: dict) -> None:
    melody_only = copy.deepcopy(two_staff_score)
    for measure in melody_only["measures"]:
        measure["events"] = [event for event in measure["events"] if event["staff"] == "right_hand"]

    result = generate_composition_candidates(
        melody_only,
        "重新和声化并保留原旋律",
        {"measures": [1, 2]},
        {},
        candidate_count=2,
        provider=_PlanningProvider(),
    )

    assert result["status"] == "unsupported"
    assert result["failure_analysis"]["code"] == "no_accompaniment_to_reharmonize"
    assert result["failure_analysis"]["counts"]["realizable_target_notes"] == 0
    assert "没有可重新和声化的伴奏音符" in result["reason"]


def test_preexisting_hand_crossing_does_not_block_a_nonworsening_edit(two_staff_score: dict) -> None:
    crossing_score = copy.deepcopy(two_staff_score)
    pitches = {
        "right_hand": ["C3", "D3", "E3", "F3"],
        "left_hand": ["C4", "B3", "A3", "G3"],
    }
    for measure in crossing_score["measures"]:
        positions = {"right_hand": 0, "left_hand": 0}
        for event in measure["events"]:
            staff = event["staff"]
            event["pitch"] = pitches[staff][positions[staff]]
            positions[staff] += 1

    result = generate_composition_candidates(
        crossing_score,
        "创作古典旋律变奏",
        {"measures": [1, 2]},
        {},
        candidate_count=2,
    )

    assert result["status"] == "generated"
    assert all(candidate["review"]["baseline_voice_crossing_count"] == 2 for candidate in result["candidates"])
    assert all(candidate["review"]["introduced_voice_crossing_count"] == 0 for candidate in result["candidates"])
    assert all(candidate["review"]["status"] == "valid" for candidate in result["candidates"])


def test_dense_multivoice_realization_preserves_each_non_crossed_hand_boundary() -> None:
    score = new_score_document(title="Dense multi-voice piano fixture", measures=8)
    voices = {
        ("right_hand", 1): ["D4", "F4", "A4", "C5"],
        ("right_hand", 2): ["D4", "E4", "F4", "G4"],
        ("right_hand", 3): ["D4", "F4", "G4", "A4"],
        ("left_hand", 2): ["C4", "G3", "B3", "A3"],
        ("left_hand", 3): ["C4", "B3", "A3", "C4"],
    }
    for measure_number, measure in enumerate(score["measures"], start=1):
        for (staff, voice), pitches in voices.items():
            for position, pitch in enumerate(pitches, start=1):
                measure["events"].append(
                    {
                        "event_id": f"m{measure_number}_{staff}_v{voice}_{position}",
                        "type": "note",
                        "pitch": pitch,
                        "duration": "quarter",
                        "offset": float(position - 1),
                        "voice": voice,
                        "staff": staff,
                        "tie": None,
                        "slur": None,
                        "accidental": "",
                        "dynamic": "mf",
                        "articulations": [],
                        "selected": False,
                    }
                )

    result = generate_composition_candidates(
        normalize_score_document(score),
        "改写八小节多声部钢琴织体，保持节奏并形成清晰终止",
        {"measures": list(range(1, 9))},
        {},
        candidate_count=3,
        search_width=8,
    )

    assert result["status"] == "generated"
    assert result["search_summary"]["valid"] == 8
    assert len(result["candidates"]) == 3
    assert all(candidate["review"]["introduced_voice_crossing_count"] == 0 for candidate in result["candidates"])
    assert all(candidate["review"]["introduced_range_violation_count"] == 0 for candidate in result["candidates"])


def test_orchestration_returns_plan_without_unsafe_patch(two_staff_score: dict) -> None:
    result = generate_composition_candidates(
        two_staff_score,
        "把这一段重新配器给弦乐四重奏",
        {"measures": [1, 2]},
        {},
    )
    assert result["status"] == "plan_only"
    assert result["apply_supported"] is False
    assert result["candidates"] == []
    assert result["plan"]["orchestration_notes"]


def test_candidate_can_patch_original_musicxml_without_rebuilding(two_staff_score: dict) -> None:
    source_musicxml = score_document_to_musicxml(two_staff_score)
    imported = musicxml_to_score_document(source_musicxml, source="composer_source_test")
    result = generate_composition_candidates(
        imported,
        "创作一个两小节古典变化",
        {"measures": [1, 2]},
        {},
        candidate_count=1,
    )
    candidate = result["candidates"][0]
    patched = patch_musicxml_preserving_source(
        source_musicxml,
        imported,
        candidate["preview"]["proposed_score_document"],
    )
    assert patched["export_mode"] == "source_preserving_patch"
    assert patched["changed_event_count"] > 0
    assert patched["changed_fields"] == ["pitch"]
    assert len(musicxml_to_score_document(patched["musicxml"])["measures"]) == 2


def test_composer_api_uses_local_fallback_without_applying(two_staff_score: dict, monkeypatch) -> None:
    monkeypatch.setenv("SERA_LLM_PROVIDER", "local_rule")
    response = TestClient(app).post(
        "/sera-edit/composer/preview",
        json={
            "score_document": two_staff_score,
            "brief": "写一个古典风格变化",
            "target_scope": {"measures": [1, 2]},
            "protected_scope": {},
            "candidate_count": 2,
            "seed": 42,
            "planner_mode": "local",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert len(payload["candidates"]) == 2
    assert payload["planner"]["planner"] == "deterministic_theory"
    assert payload["planner"]["timeout_seconds"] == 180.0
    assert all(candidate["preview"]["committed"] is False for candidate in payload["candidates"])


def test_composer_caps_live_planner_wait_before_local_fallback(two_staff_score: dict, monkeypatch) -> None:
    captured: dict[str, float] = {}
    settings = LLMRuntimeSettings(
        provider="deepseek",
        model="test-model",
        base_url="https://api.deepseek.com/v1",
        api_key_env="SERA_LLM_API_KEY",
        configured=True,
        available=True,
        transport="chat_completions",
        fallback_local=True,
        timeout_seconds=90.0,
        max_output_tokens=4000,
        reasoning_effort="low",
        store=False,
        supports_structured_outputs=False,
        input_cost_per_million=None,
        output_cost_per_million=None,
        config_file="test.env",
        reason="ready",
    )

    def _provider(resolved: LLMRuntimeSettings) -> _PlanningProvider:
        captured["timeout_seconds"] = resolved.timeout_seconds
        return _PlanningProvider()

    monkeypatch.setattr("sera_edit.composer.pipeline.create_runtime_provider", _provider)
    result = compose_with_runtime(
        two_staff_score,
        "创作一个浪漫主义变化",
        {"measures": [1, 2]},
        {},
        settings=settings,
    )
    assert result["status"] == "generated"
    assert captured["timeout_seconds"] == 180.0
    assert result["planner"]["timeout_seconds"] == 180.0


def test_composer_timeout_override_is_safely_bounded(monkeypatch) -> None:
    monkeypatch.setenv("SERA_COMPOSER_LLM_TIMEOUT_SECONDS", "2")
    assert composer_llm_timeout_seconds() == 30.0
    monkeypatch.setenv("SERA_COMPOSER_LLM_TIMEOUT_SECONDS", "120")
    assert composer_llm_timeout_seconds() == 120.0
    monkeypatch.setenv("SERA_COMPOSER_LLM_TIMEOUT_SECONDS", "900")
    assert composer_llm_timeout_seconds() == 600.0
    monkeypatch.setenv("SERA_COMPOSER_LLM_TIMEOUT_SECONDS", "invalid")
    assert composer_llm_timeout_seconds() == 180.0


def test_responsive_composer_returns_local_draft_before_slow_llm(two_staff_score: dict) -> None:
    provider = _BlockingPlanningProvider()
    settings = LLMRuntimeSettings(
        provider="deepseek",
        model="slow-test-model",
        base_url="https://api.deepseek.com/v1",
        api_key_env="SERA_LLM_API_KEY",
        configured=True,
        available=True,
        transport="chat_completions",
        fallback_local=True,
        timeout_seconds=90.0,
        max_output_tokens=4000,
        reasoning_effort="medium",
        store=False,
        supports_structured_outputs=False,
        input_cost_per_million=None,
        output_cost_per_million=None,
        config_file="test.env",
        reason="ready",
    )
    store = default_composer_refinement_store()
    store.clear()

    result = compose_responsive_with_runtime(
        two_staff_score,
        "创作一个有清晰终止的古典变化",
        {"measures": [1, 2]},
        {},
        settings=settings,
        provider=provider,
    )

    assert provider.started.is_set()
    assert result["status"] == "generated"
    assert result["planner"]["planner"] == "deterministic_theory"
    assert result["refinement"]["status"] == "running"
    assert result["search_summary"]["search_width"] == 8
    provider.release.set()

    deadline = time.monotonic() + 10
    snapshot = store.get(result["refinement"]["job_id"])
    while snapshot["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
        snapshot = store.get(result["refinement"]["job_id"])
    assert snapshot["status"] == "ready"
    assert snapshot["result"]["planner"]["planner"] == "live_llm"
    assert provider.max_tokens == composer_llm_max_output_tokens() == 2048
    store.clear()


def test_composer_refinement_poll_endpoint_returns_ready_result() -> None:
    store = default_composer_refinement_store()
    store.clear()
    started = store.start(lambda: {"planner": {"planner": "live_llm"}, "status": "generated"})
    deadline = time.monotonic() + 2
    response = TestClient(app).get(f"/sera-edit/composer/refinements/{started['job_id']}")
    while response.json()["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.02)
        response = TestClient(app).get(f"/sera-edit/composer/refinements/{started['job_id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["result"]["planner"]["planner"] == "live_llm"
    store.clear()

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.providers.base import ProviderResponse
from sera_edit.providers.runtime import MANAGED_ENV_KEYS


@pytest.fixture(autouse=True)
def _force_local_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """API tests must never consume a developer's configured live key."""

    monkeypatch.setenv("SERA_LLM_PROVIDER", "local_rule")


def _patch(score: dict) -> dict:
    return {
        "schema_version": "1.0.0",
        "patch_id": "api_patch_001",
        "source_score_id": score["score_id"],
        "source_fingerprint": score_fingerprint(score),
        "instruction": "Transpose one note.",
        "target_scope": {"event_ids": ["m1_rh_1"]},
        "protected_scope": {"staffs": [2]},
        "preconditions": [],
        "operations": [{"operation_id": "api_op_001", "type": "transpose", "selector": {"event_ids": ["m1_rh_1"]}, "arguments": {"semitones": 2}, "preconditions": [], "expected_change_count": 1}],
        "expected_effects": [{"type": "preserve_duration"}],
        "provenance": {"provider": "mock", "model": "test"},
    }


def test_preview_returns_proposed_score_without_commit(two_staff_score: dict) -> None:
    response = TestClient(app).post(
        "/sera-edit/preview",
        json={"score_document": two_staff_score, "patch": _patch(two_staff_score)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["committed"] is False
    assert payload["proposed_score_document"]["measures"][0]["events"][0]["pitch"] == "D4"
    assert payload["score_document"]["measures"][0]["events"][0]["pitch"] == "C4"


def test_apply_commits_strict_patch(two_staff_score: dict) -> None:
    response = TestClient(app).post(
        "/sera-edit/apply",
        json={"score_document": two_staff_score, "patch": _patch(two_staff_score)},
    )
    assert response.status_code == 200
    assert response.json()["committed"] is True


def test_generate_preview_returns_strict_local_patch_and_proposal(two_staff_score: dict) -> None:
    response = TestClient(app).post(
        "/sera-edit/generate-preview",
        json={
            "score_document": two_staff_score,
            "instruction": "将第一小节右手升高大二度，并保持节奏不变。",
            "target_scope": {"measures": [1], "staffs": [1]},
            "protected_scope": {"staffs": [2]},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["generator"]["formal_experiment_eligible"] is False
    assert payload["preview"]["validation_report"]["status"] == "valid"
    assert payload["preview"]["proposed_score_document"]["measures"][0]["events"][0]["pitch"] == "D4"


def test_generate_preview_promotes_host_selection_for_global_key_without_transposing(two_staff_score: dict) -> None:
    response = TestClient(app).post(
        "/sera-edit/generate-preview",
        json={
            "score_document": two_staff_score,
            "instruction": "将调号改为G major，但不要移调音符。",
            "target_scope": {"measures": [1, 2]},
            "protected_scope": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    proposed = payload["preview"]["proposed_score_document"]
    source_pitches = [event.get("pitch") for measure in two_staff_score["measures"] for event in measure["events"]]
    proposed_pitches = [event.get("pitch") for measure in proposed["measures"] for event in measure["events"]]
    assert payload["status"] == "generated"
    assert payload["generator"]["routing"] == "local_first"
    assert payload["patch"]["target_scope"]["whole_score"] is True
    assert payload["preview"]["validation_report"]["status"] == "valid"
    assert payload["preview"]["diff"]["changed_element_count"] == 1
    assert payload["preview"]["diff"]["global_changes"]["key"] == {"before": "C major", "after": "G major"}
    assert source_pitches == proposed_pitches


def test_generate_preview_promotes_mixed_meter_rebar_and_returns_real_diff(two_staff_score: dict) -> None:
    response = TestClient(app).post(
        "/sera-edit/generate-preview",
        json={
            "score_document": two_staff_score,
            "instruction": (
                "Rebar the selected excerpt from 4/4 to 3/4 by removing the final quarter-note event "
                "from each staff in every measure; preserve every remaining pitch and duration."
            ),
            "target_scope": {"measures": [1, 2]},
            "protected_scope": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["patch"]["target_scope"]["whole_score"] is True
    assert [operation["type"] for operation in payload["patch"]["operations"]] == [
        "change_time_signature",
        "delete_event",
    ]
    assert payload["preview"]["validation_report"]["status"] == "valid"
    assert payload["preview"]["validation_report"]["errors"] == []
    assert payload["preview"]["diff"]["global_changes"]["meter"] == {"before": "4/4", "after": "3/4"}
    assert len(payload["preview"]["diff"]["deleted"]) == 4
    assert sum(len(measure["events"]) for measure in payload["preview"]["proposed_score_document"]["measures"]) == 12


def test_generate_preview_returns_explicit_unsupported_without_patch(two_staff_score: dict) -> None:
    response = TestClient(app).post(
        "/sera-edit/generate-preview",
        json={
            "score_document": two_staff_score,
            "instruction": "让它更有海浪的感觉",
            "target_scope": {"measures": [1]},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unsupported"
    assert payload["patch"] is None
    assert payload["preview"] is None


def test_generate_preview_routes_melody_rewrite_through_composer(two_staff_score: dict) -> None:
    response = TestClient(app).post(
        "/sera-edit/generate-preview",
        json={
            "score_document": two_staff_score,
            "instruction": "重写当前选区的旋律，保持节奏和声部数量不变，并形成清晰终止。",
            "target_scope": {"measures": [1, 2], "staffs": [1]},
            "protected_scope": {"staffs": [2]},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["generator"]["composition_route"] is True
    assert payload["generator"]["candidate_count"] == 3
    assert payload["composition_evidence"]["selected_review"]["status"] == "valid"
    assert payload["preview"]["validation_report"]["status"] == "valid"
    assert payload["preview"]["diff"]["changed"]
    assert all(operation["type"] == "set_pitch" for operation in payload["patch"]["operations"])
    assert all(item["changed_fields"] == ["pitch"] for item in payload["preview"]["diff"]["changed"])


def test_live_provider_route_returns_validated_patch_without_exposing_key(
    two_staff_score: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeLiveProvider:
        provider = "openai"
        model = "test-live-model"

        def generate(self, *_: object, **__: object) -> ProviderResponse:
            return ProviderResponse(
                raw_text="{}",
                parsed_output={
                    "status": "patch",
                    "reason": "",
                    "operations": [
                        {
                            "type": "transpose",
                            "apply_to_all_selected": True,
                            "event_ids": [],
                            "semitones": 2,
                            "pitch": "",
                            "dynamic": "",
                            "articulations": [],
                        }
                    ],
                },
                provider="openai",
                model="test-live-model",
                latency_ms=10,
                input_tokens=100,
                output_tokens=30,
                request_id="resp_test_route",
            )

    monkeypatch.setenv("SERA_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SERA_LLM_MODEL", "test-live-model")
    monkeypatch.setenv("SERA_LLM_API_KEY", "route-secret-not-for-output")
    monkeypatch.setattr(
        "sera_edit.generation.llm_patch_generator.create_runtime_provider",
        lambda settings: FakeLiveProvider(),
    )

    response = TestClient(app).post(
        "/sera-edit/generate-preview",
        json={
            "score_document": two_staff_score,
            "instruction": "Transpose the upper staff up by a major second.",
            "target_scope": {"measures": [1], "staffs": [1]},
            "protected_scope": {"staffs": [2]},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["generator"]["live"] is True
    assert payload["generator"]["request_id"] == "resp_test_route"
    assert payload["preview"]["validation_report"]["status"] == "valid"
    assert "route-secret-not-for-output" not in response.text


def test_provider_status_endpoint_is_credential_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERA_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SERA_LLM_MODEL", "test-status-model")
    monkeypatch.setenv("SERA_LLM_API_KEY", "status-secret-not-for-output")

    response = TestClient(app).get("/sera-edit/provider-status")

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["transport"] == "responses"
    assert "status-secret-not-for-output" not in response.text


def test_chat_route_answers_without_generating_or_applying_a_patch(
    two_staff_score: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeConversationProvider:
        provider = "openai"
        model = "test-conversation-model"

        def generate(self, messages: list[dict[str, str]], **_: object) -> ProviderResponse:
            assert "conversation-only channel" in messages[0]["content"]
            return ProviderResponse(
                raw_text="大二度通常等于 **两个半音**。普通对话不会修改你的乐谱。",
                parsed_output=None,
                provider=self.provider,
                model=self.model,
                latency_ms=8,
                input_tokens=50,
                output_tokens=20,
                request_id="conversation_test_1",
            )

    monkeypatch.setenv("SERA_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SERA_LLM_MODEL", "test-conversation-model")
    monkeypatch.setenv("SERA_LLM_API_KEY", "conversation-secret-not-for-output")
    monkeypatch.setattr(
        "sera_edit.generation.conversation_agent.create_runtime_provider",
        lambda settings: FakeConversationProvider(),
    )

    response = TestClient(app).post(
        "/sera-edit/chat",
        json={
            "message": "大二度是多少个半音？",
            "history": [{"role": "user", "content": "先解释音程。"}],
            "score_document": two_staff_score,
            "target_scope": {"measures": [1]},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert "两个半音" in payload["answer"]
    assert "**" not in payload["answer"]
    assert "patch" not in payload
    assert "preview" not in payload
    assert "conversation-secret-not-for-output" not in response.text


def test_provider_configuration_endpoint_encrypts_and_never_echoes_key(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in MANAGED_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    config_path = tmp_path / "Sera" / "llm.env"
    monkeypatch.setenv("SERA_LLM_ENV_FILE", str(config_path))
    monkeypatch.setattr("sera_edit.providers.runtime.protect_secret", lambda _: "encrypted-test-value")
    monkeypatch.setattr("sera_edit.providers.runtime.unprotect_secret", lambda _: "ui-secret-not-for-output")

    response = TestClient(app).put(
        "/sera-edit/provider-configuration",
        json={
            "provider": "openai",
            "model": "test-ui-model",
            "base_url": "https://api.example.test/v1",
            "api_key": "ui-secret-not-for-output",
            "fallback_local": True,
            "reasoning_effort": "low",
            "composer_timeout_seconds": 240,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"]["available"] is True
    assert response.json()["status"]["credential_storage"] == "windows_dpapi"
    assert response.json()["status"]["composer_timeout_seconds"] == 240
    assert "ui-secret-not-for-output" not in response.text
    assert "ui-secret-not-for-output" not in config_path.read_text(encoding="utf-8")
    assert "encrypted-test-value" in config_path.read_text(encoding="utf-8")
    assert "SERA_COMPOSER_LLM_TIMEOUT_SECONDS=240" in config_path.read_text(encoding="utf-8")

    cleared = TestClient(app).delete("/sera-edit/provider-configuration")
    assert cleared.status_code == 200
    assert cleared.json()["status"]["provider"] == "local_rule"
    assert "encrypted-test-value" not in config_path.read_text(encoding="utf-8")


def test_provider_configuration_rejects_insecure_remote_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sera_edit.providers.runtime.protect_secret", lambda _: "encrypted-test-value")
    response = TestClient(app).put(
        "/sera-edit/provider-configuration",
        json={
            "provider": "openai-compatible",
            "model": "unsafe-model",
            "base_url": "http://remote.example.test/v1",
            "api_key": "never-written-secret",
        },
    )

    assert response.status_code == 400
    assert "HTTPS" in response.json()["detail"]
    assert "never-written-secret" not in response.text

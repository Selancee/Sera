from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from evaluation.runners.experiment_runner import _validate_config
from evaluation.runners.runtime_controls import BudgetExceeded, BudgetLedger, ControlledProvider
from sera_edit.generation.prompts import build_condition_messages
from sera_edit.generation.response_parser import extract_musicxml, parse_json_object
from sera_edit.providers.base import ProviderRequestError, ProviderResponse
from sera_edit.providers.credential_protection import protect_secret, unprotect_secret
from sera_edit.providers.deepseek_provider import DeepSeekProvider
from sera_edit.providers.openai_provider import OpenAIProvider
from sera_edit.providers.openai_responses import OpenAIResponsesProvider
from sera_edit.providers.runtime import (
    MANAGED_ENV_KEYS,
    clear_runtime_configuration,
    runtime_settings,
    save_runtime_configuration,
)


class _FakeHttpResponse:
    status_code = 200
    headers = {"x-request-id": "header-request"}
    text = ""

    def json(self) -> dict[str, Any]:
        return {
            "id": "request-123",
            "model": "test-model-snapshot",
            "choices": [
                {
                    "message": {"content": '{"schema_version":"1.0.0"}'},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _FakeHttpResponse:
        self.calls.append({"url": url, **kwargs})
        return _FakeHttpResponse()


class _FakeResponsesHttpResponse:
    status_code = 200
    headers = {"x-request-id": "responses-header-request"}
    text = ""

    def json(self) -> dict[str, Any]:
        return {
            "id": "resp_123",
            "model": "test-responses-snapshot",
            "status": "completed",
            "output": [
                {
                    "type": "reasoning",
                    "id": "reasoning_1",
                },
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"status":"patch","reason":"","operations":[]}',
                        }
                    ],
                },
            ],
            "usage": {"input_tokens": 120, "output_tokens": 30},
        }


class _FakeResponsesSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _FakeResponsesHttpResponse:
        self.calls.append({"url": url, **kwargs})
        return _FakeResponsesHttpResponse()


class _FlakyProvider:
    provider = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, *args: Any, **kwargs: Any) -> ProviderResponse:
        del args, kwargs
        self.calls += 1
        if self.calls == 1:
            raise ProviderRequestError("temporary", retryable=True)
        return ProviderResponse("{}", {}, self.provider, self.model, 1.0, 2, 3, 0.01)


def test_openai_provider_uses_environment_key_and_records_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERA_TEST_OPENAI_KEY", "secret-not-for-output")
    session = _FakeSession()
    provider = OpenAIProvider(
        model="test-model",
        base_url="https://api.example.test/v1",
        api_key_env="SERA_TEST_OPENAI_KEY",
        timeout_seconds=12,
        input_cost_per_million=2.0,
        output_cost_per_million=4.0,
        supports_structured_outputs=True,
        session=session,
    )
    response = provider.generate(
        [{"role": "user", "content": "return json"}],
        response_schema={"type": "object"},
        seed=42,
        max_tokens=50,
    )
    assert session.calls[0]["url"] == "https://api.example.test/v1/chat/completions"
    assert session.calls[0]["json"]["response_format"]["type"] == "json_schema"
    assert session.calls[0]["headers"]["Authorization"] == "Bearer secret-not-for-output"
    assert response.parsed_output == {"schema_version": "1.0.0"}
    assert response.input_tokens == 100 and response.output_tokens == 50
    assert response.estimated_cost == pytest.approx(0.0004)
    assert "secret-not-for-output" not in json.dumps(response.as_dict())


def test_deepseek_provider_uses_json_object_mode_for_server_validated_plans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SERA_TEST_DEEPSEEK_KEY", "deepseek-secret-not-for-output")
    session = _FakeSession()
    provider = DeepSeekProvider(
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        api_key_env="SERA_TEST_DEEPSEEK_KEY",
        session=session,
    )

    provider.generate(
        [{"role": "user", "content": "return json"}],
        response_schema={"type": "object"},
        max_tokens=2048,
        metadata={"purpose": "composition_plan", "thinking": "disabled"},
    )

    assert session.calls[0]["json"]["response_format"] == {"type": "json_object"}
    assert session.calls[0]["json"]["max_tokens"] == 2048
    assert session.calls[0]["json"]["thinking"] == {"type": "disabled"}


def test_openai_responses_provider_uses_strict_schema_and_collects_all_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SERA_TEST_RESPONSES_KEY", "responses-secret-not-for-output")
    session = _FakeResponsesSession()
    provider = OpenAIResponsesProvider(
        model="test-responses-model",
        base_url="https://api.example.test/v1",
        api_key_env="SERA_TEST_RESPONSES_KEY",
        reasoning_effort="low",
        session=session,
    )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "reason", "operations"],
        "properties": {
            "status": {"type": "string"},
            "reason": {"type": "string"},
            "operations": {"type": "array", "items": {"type": "string"}},
        },
    }
    response = provider.generate(
        [{"role": "user", "content": "edit the selected score"}],
        response_schema=schema,
        max_tokens=900,
    )

    call = session.calls[0]
    assert call["url"] == "https://api.example.test/v1/responses"
    assert call["json"]["text"]["format"]["type"] == "json_schema"
    assert call["json"]["text"]["format"]["strict"] is True
    assert call["json"]["max_output_tokens"] == 900
    assert response.parsed_output == {"status": "patch", "reason": "", "operations": []}
    assert response.input_tokens == 120 and response.output_tokens == 30
    assert "responses-secret-not-for-output" not in json.dumps(response.as_dict())


def test_runtime_status_never_returns_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERA_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SERA_LLM_MODEL", "test-model")
    monkeypatch.setenv("SERA_LLM_API_KEY", "runtime-secret-not-for-output")
    monkeypatch.delenv("SERA_LLM_API_KEY_ENV", raising=False)

    status = runtime_settings().public_status()

    assert status["available"] is True
    assert status["transport"] == "responses"
    assert status["api_key_configured"] is True
    assert "runtime-secret-not-for-output" not in json.dumps(status)


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI is the desktop credential store")
def test_windows_dpapi_round_trip_does_not_embed_plaintext() -> None:
    secret = f"sera-test-{uuid4()}"
    protected_value = protect_secret(secret)

    assert secret not in protected_value
    assert unprotect_secret(protected_value) == secret


def test_in_app_runtime_configuration_encrypts_file_and_activates_immediately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in MANAGED_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    config_path = tmp_path / "Sera" / "llm.env"
    monkeypatch.setenv("SERA_LLM_ENV_FILE", str(config_path))
    monkeypatch.setattr("sera_edit.providers.runtime.protect_secret", lambda value: f"cipher:{len(value)}")
    monkeypatch.setattr("sera_edit.providers.runtime.unprotect_secret", lambda _: "in-app-secret")

    settings = save_runtime_configuration(
        provider="openai",
        model="test-live-model",
        api_key="in-app-secret",
        base_url="https://api.example.test/v1",
        fallback_local=True,
        reasoning_effort="low",
    )
    stored = config_path.read_text(encoding="utf-8")
    status = settings.public_status()

    assert settings.available is True
    assert "in-app-secret" not in stored
    assert "SERA_LLM_API_KEY_ENCRYPTED=cipher:13" in stored
    assert status["credential_storage"] == "windows_dpapi"
    assert "in-app-secret" not in json.dumps(status)
    assert os.environ["SERA_LLM_API_KEY"] == "in-app-secret"

    updated = save_runtime_configuration(
        provider="openai",
        model="test-live-model-v2",
        api_key=None,
        base_url="https://api.example.test/v1",
    )
    assert updated.model == "test-live-model-v2"
    assert os.environ["SERA_LLM_API_KEY"] == "in-app-secret"

    local = clear_runtime_configuration()
    assert local.provider == "local_rule"
    assert "SERA_LLM_API_KEY_ENCRYPTED" not in config_path.read_text(encoding="utf-8")
    assert "SERA_LLM_API_KEY" not in os.environ


def test_controlled_provider_retries_then_caches(tmp_path: Path) -> None:
    inner = _FlakyProvider()
    ledger = BudgetLedger(1.0, 1.0, 1.0)
    provider = ControlledProvider(
        inner,
        cache_root=tmp_path,
        cache_enabled=True,
        max_retries=1,
        retry_backoff_seconds=0,
        requests_per_minute=None,
        budget=ledger,
        sleeper=lambda _: None,
    )
    messages = [{"role": "user", "content": "hello"}]
    first = provider.generate(messages, max_tokens=5)
    second = provider.generate(messages, max_tokens=5)
    assert inner.calls == 2
    assert first.retry_count == 1 and first.cached is False
    assert second.cached is True
    assert first.request_hash == second.request_hash


def test_budget_blocks_request_before_provider_call(tmp_path: Path) -> None:
    inner = _FlakyProvider()
    provider = ControlledProvider(
        inner,
        cache_root=tmp_path,
        cache_enabled=False,
        max_retries=0,
        retry_backoff_seconds=0,
        requests_per_minute=None,
        budget=BudgetLedger(0.000001, 1.0, 1.0),
        sleeper=lambda _: None,
    )
    with pytest.raises(BudgetExceeded):
        provider.generate([{"role": "user", "content": "hello"}], max_tokens=5)
    assert inner.calls == 0


def test_prompts_preserve_condition_boundaries(two_staff_score: dict) -> None:
    task = {
        "instruction_en": "Transpose one measure.",
        "target_scope": {"measures": [1], "staffs": [1]},
        "protected_scope": {"staffs": [2]},
        "expected_constraints": [{"type": "pitch_delta", "value": 2}],
        "expected_status": "success",
        "unsupported_reason": None,
    }
    rewrite, rewrite_schema = build_condition_messages("full_rewrite", task, two_staff_score)
    patch_only, patch_schema = build_condition_messages("patch_only", task, two_staff_score)
    full, full_schema = build_condition_messages("sera_full", task, two_staff_score)
    assert "<score-partwise" in rewrite[1]["content"] and rewrite_schema is None
    assert "protected_scope" not in json.loads(patch_only[1]["content"])
    assert "protected_scope" in json.loads(full[1]["content"])
    assert patch_schema != full_schema
    assert full_schema is not None and len(full_schema["oneOf"]) == 2
    refusal_schema = full_schema["oneOf"][1]
    assert refusal_schema["properties"]["refusal"]["const"] is True


def test_response_cleanup_is_bounded() -> None:
    assert parse_json_object("```json\n{\"ok\": true}\n```") == {"ok": True}
    xml = extract_musicxml("prefix\n```xml\n<score-partwise version=\"4.0\"></score-partwise>\n```\nsuffix")
    assert xml == '<score-partwise version="4.0"></score-partwise>'


def test_formal_config_rejects_mock_and_missing_prices() -> None:
    base = {
        "conditions": ["sera_full"],
        "repetitions": 1,
        "max_concurrency": 1,
        "formal_results_allowed": True,
        "budget_limit_usd": 1,
    }
    with pytest.raises(ValueError, match="mock"):
        _validate_config({**base, "provider": {"provider": "mock"}})
    with pytest.raises(ValueError, match="prices"):
        _validate_config({**base, "provider": {"provider": "qwen"}})

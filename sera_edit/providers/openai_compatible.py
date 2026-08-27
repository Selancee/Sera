"""Credential-safe synchronous adapter for OpenAI-compatible chat-completion APIs."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse

import requests

from sera_edit.generation.response_parser import parse_json_object
from sera_edit.providers.base import ProviderRequestError, ProviderResponse


class OpenAICompatibleProvider:
    """Call a configured `/chat/completions` endpoint without persisting API keys."""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        base_url: str,
        api_key_env: str,
        timeout_seconds: float = 90.0,
        input_cost_per_million: float | None = None,
        output_cost_per_million: float | None = None,
        supports_structured_outputs: bool = False,
        session: requests.Session | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"invalid provider base_url: {base_url}")
        if not model.strip():
            raise ValueError("provider model must be configured")
        if not api_key_env.strip():
            raise ValueError("api_key_env must be configured")
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"required provider credential is missing from environment variable {api_key_env}")
        self.provider = provider
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self._api_key = api_key
        self.timeout_seconds = float(timeout_seconds)
        self.input_cost_per_million = input_cost_per_million
        self.output_cost_per_million = output_cost_per_million
        self.supports_structured_outputs = supports_structured_outputs
        self.session = session or requests.Session()

    @property
    def endpoint(self) -> str:
        """Return the configured Chat Completions URL."""

        return f"{self.base_url}/chat/completions"

    def generate(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Generate one response and capture tokens, request ID, latency, and estimated cost."""

        payload: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": temperature}
        if seed is not None:
            payload["seed"] = seed
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_schema is not None and self.supports_structured_outputs:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "score_patch", "strict": True, "schema": response_schema},
            }
        elif response_schema is not None and self.provider == "deepseek":
            # DeepSeek exposes JSON Object mode rather than OpenAI's strict
            # json_schema envelope.  The caller still validates the returned
            # object against the server-owned schema.
            payload["response_format"] = {"type": "json_object"}
        if self.provider == "deepseek" and metadata is not None:
            thinking = str(metadata.get("thinking") or "").strip().lower()
            if thinking in {"enabled", "disabled"}:
                # DeepSeek V4 defaults to thinking mode.  Tiny server-validated
                # JSON plans do not benefit from spending the output budget on
                # hidden reasoning, so callers can explicitly disable it without
                # changing the user's normal chat/reasoning preference.
                payload["thinking"] = {"type": thinking}
        started = time.perf_counter()
        try:
            response = self.session.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderRequestError(f"{self.provider} request failed: {exc}", retryable=True) from exc
        latency_ms = (time.perf_counter() - started) * 1000
        if response.status_code >= 400:
            retryable = response.status_code in {408, 409, 425, 429} or response.status_code >= 500
            retry_after = response.headers.get("Retry-After")
            try:
                retry_after_seconds = float(retry_after) if retry_after is not None else None
            except ValueError:
                retry_after_seconds = None
            detail = response.text.strip().replace("\r", " ").replace("\n", " ")[:500]
            raise ProviderRequestError(
                f"{self.provider} returned HTTP {response.status_code}: {detail}",
                retryable=retryable,
                status_code=response.status_code,
                retry_after_seconds=retry_after_seconds,
            )
        try:
            data = response.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderRequestError(f"{self.provider} returned an invalid chat-completion response", retryable=False) from exc
        if isinstance(content, list):
            content = "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
        raw_text = str(content or "")
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        estimated_cost = None
        if self.input_cost_per_million is not None and self.output_cost_per_million is not None:
            estimated_cost = (
                input_tokens * float(self.input_cost_per_million)
                + output_tokens * float(self.output_cost_per_million)
            ) / 1_000_000
        return ProviderResponse(
            raw_text=raw_text,
            parsed_output=parse_json_object(raw_text),
            provider=self.provider,
            model=str(data.get("model") or self.model),
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            request_id=str(data.get("id") or response.headers.get("x-request-id") or "") or None,
            finish_reason=str(choice.get("finish_reason") or "") or None,
        )

"""Credential-safe OpenAI Responses API adapter for interactive score editing."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse

import requests

from sera_edit.generation.response_parser import parse_json_object
from sera_edit.providers.base import ProviderRequestError, ProviderResponse


class OpenAIResponsesProvider:
    """Call OpenAI Responses with an optional strict JSON Schema output format."""

    provider = "openai"

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key_env: str,
        timeout_seconds: float = 90.0,
        reasoning_effort: str = "low",
        store: bool = False,
        input_cost_per_million: float | None = None,
        output_cost_per_million: float | None = None,
        session: requests.Session | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"invalid OpenAI base_url: {base_url}")
        if not model.strip():
            raise ValueError("OpenAI model must be configured")
        if not api_key_env.strip():
            raise ValueError("OpenAI api_key_env must be configured")
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"required OpenAI credential is missing from environment variable {api_key_env}")
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self._api_key = api_key
        self.timeout_seconds = float(timeout_seconds)
        self.reasoning_effort = reasoning_effort.strip().lower()
        self.store = bool(store)
        self.input_cost_per_million = input_cost_per_million
        self.output_cost_per_million = output_cost_per_million
        self.session = session or requests.Session()

    @property
    def endpoint(self) -> str:
        """Return the configured Responses API endpoint."""

        return f"{self.base_url}/responses"

    def generate(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Generate one response without exposing credentials to traces or callers."""

        del temperature, seed, metadata
        payload: dict[str, Any] = {
            "model": self.model,
            "input": messages,
            "store": self.store,
        }
        if max_tokens is not None:
            payload["max_output_tokens"] = int(max_tokens)
        if self.reasoning_effort:
            payload["reasoning"] = {"effort": self.reasoning_effort}
        if response_schema is not None:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "sera_score_patch_proposal",
                    "strict": True,
                    "schema": response_schema,
                }
            }

        started = time.perf_counter()
        try:
            response = self.session.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderRequestError(
                self._sanitize(f"OpenAI request failed: {exc}"),
                retryable=True,
            ) from exc
        latency_ms = (time.perf_counter() - started) * 1000
        if response.status_code >= 400:
            retryable = response.status_code in {408, 409, 425, 429} or response.status_code >= 500
            retry_after = response.headers.get("Retry-After")
            try:
                retry_after_seconds = float(retry_after) if retry_after is not None else None
            except ValueError:
                retry_after_seconds = None
            detail = self._sanitize(response.text.strip().replace("\r", " ").replace("\n", " ")[:500])
            raise ProviderRequestError(
                f"OpenAI returned HTTP {response.status_code}: {detail}",
                retryable=retryable,
                status_code=response.status_code,
                retry_after_seconds=retry_after_seconds,
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderRequestError("OpenAI returned invalid JSON", retryable=False) from exc

        raw_text, refusal = _response_text_and_refusal(data)
        parsed_output = parse_json_object(raw_text)
        if parsed_output is None and refusal:
            parsed_output = {"status": "refusal", "reason": refusal, "operations": []}
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        estimated_cost = None
        if self.input_cost_per_million is not None and self.output_cost_per_million is not None:
            estimated_cost = (
                input_tokens * float(self.input_cost_per_million)
                + output_tokens * float(self.output_cost_per_million)
            ) / 1_000_000
        incomplete = data.get("incomplete_details") or {}
        finish_reason = str(incomplete.get("reason") or data.get("status") or "") or None
        return ProviderResponse(
            raw_text=raw_text,
            parsed_output=parsed_output,
            provider=self.provider,
            model=str(data.get("model") or self.model),
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            request_id=str(data.get("id") or response.headers.get("x-request-id") or "") or None,
            finish_reason=finish_reason,
        )

    def _sanitize(self, value: str) -> str:
        return value.replace(self._api_key, "[redacted]")


def _response_text_and_refusal(data: dict[str, Any]) -> tuple[str, str]:
    """Collect text from all message output items instead of assuming output[0]."""

    texts: list[str] = []
    refusals: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") == "output_text" and content.get("text"):
                texts.append(str(content["text"]))
            elif content.get("type") == "refusal" and content.get("refusal"):
                refusals.append(str(content["refusal"]))
    if not texts and data.get("output_text"):
        texts.append(str(data["output_text"]))
    return "\n".join(texts).strip(), "\n".join(refusals).strip()

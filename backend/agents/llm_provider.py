"""Minimal LLM provider adapter for Sera agents.

The MVP runs in mock mode by default. A real provider can be enabled with
environment variables without hardcoding credentials:

SERA_LLM_PROVIDER=openai
OPENAI_API_KEY=...
SERA_LLM_BASE_URL=https://api.openai.com/v1
SERA_LLM_MODEL=gpt-4.1-mini

TODO: Replace the small HTTP adapter with a provider registry when multiple
OpenAI-compatible, local, and academic model backends are needed.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(slots=True)
class LLMProviderResult:
    """Result returned by an optional LLM provider call."""

    provider: str
    model: str
    text: str
    used_live_provider: bool
    error: str | None = None


class LLMProvider:
    """Small OpenAI-compatible text adapter with a safe mock fallback."""

    def __init__(self) -> None:
        self.provider = os.getenv("SERA_LLM_PROVIDER", "mock").lower()
        self.model = os.getenv("SERA_LLM_MODEL", "gpt-4.1-mini")
        self.base_url = os.getenv("SERA_LLM_BASE_URL", "https://api.openai.com/v1")
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def complete_json(self, system_prompt: str, user_prompt: str) -> LLMProviderResult:
        """Request a JSON-oriented completion, or return a mock result.

        The method intentionally returns text only. Downstream agents decide
        whether and how to parse the response so failures stay local.
        """

        if self.provider == "mock" or not self.api_key:
            return LLMProviderResult(
                provider="mock",
                model="mock-rule-system",
                text="{}",
                used_live_provider=False,
            )

        if self.provider not in {"openai", "openai-compatible"}:
            return LLMProviderResult(
                provider=self.provider,
                model=self.model,
                text="{}",
                used_live_provider=False,
                error=f"Unsupported provider: {self.provider}",
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
            text = body["choices"][0]["message"]["content"]
            return LLMProviderResult(
                provider=self.provider,
                model=self.model,
                text=text,
                used_live_provider=True,
            )
        except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
            return LLMProviderResult(
                provider=self.provider,
                model=self.model,
                text="{}",
                used_live_provider=False,
                error=str(exc),
            )

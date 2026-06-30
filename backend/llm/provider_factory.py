"""Provider factory for score-editing LLM calls.

All live providers use an OpenAI-compatible chat completions shape.  Missing
API keys or runtime errors return a mock result so Workbench editing remains
usable without external services.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from backend.llm.base import LLMCallResult


class MockLLMProvider:
    """No-network provider used for tests and API-key-free demos."""

    provider = "mock"
    model = "mock-rule-system"

    def available(self) -> bool:
        return False

    def complete_json(self, system_prompt: str, user_prompt: str) -> LLMCallResult:
        del system_prompt, user_prompt
        return LLMCallResult(
            provider=self.provider,
            model=self.model,
            text="{}",
            used_live_provider=False,
            latency_ms=0.0,
            error="mock provider",
            raw_response={},
        )


class OpenAICompatibleProvider:
    """Tiny HTTP adapter for OpenAI, DeepSeek, Qwen, and compatible gateways."""

    def __init__(self, provider: str, model: str, base_url: str, api_key: str) -> None:
        self.provider = provider
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def available(self) -> bool:
        return bool(self.api_key)

    def complete_json(self, system_prompt: str, user_prompt: str) -> LLMCallResult:
        started = time.perf_counter()
        if not self.available():
            return LLMCallResult(
                provider=self.provider,
                model=self.model,
                text="{}",
                used_live_provider=False,
                latency_ms=0.0,
                error="missing API key",
                raw_response={},
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
            text = body["choices"][0]["message"]["content"]
            return LLMCallResult(
                provider=self.provider,
                model=self.model,
                text=text,
                used_live_provider=True,
                latency_ms=(time.perf_counter() - started) * 1000,
                raw_response=body,
            )
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            return LLMCallResult(
                provider=self.provider,
                model=self.model,
                text="{}",
                used_live_provider=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=str(exc),
                raw_response={},
            )


def create_llm_provider() -> MockLLMProvider | OpenAICompatibleProvider:
    """Create the configured provider, falling back to mock when incomplete."""

    provider = os.getenv("SERA_LLM_PROVIDER", "mock").strip().lower()
    if provider in {"", "mock"}:
        return MockLLMProvider()

    if provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleProvider(
            provider="openai",
            model=os.getenv("SERA_LLM_MODEL", "gpt-4.1-mini"),
            base_url=os.getenv("SERA_LLM_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("SERA_LLM_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
        )
    if provider == "deepseek":
        return OpenAICompatibleProvider(
            provider="deepseek",
            model=os.getenv("SERA_LLM_MODEL", "deepseek-chat"),
            base_url=os.getenv("SERA_LLM_BASE_URL", "https://api.deepseek.com/v1"),
            api_key=os.getenv("SERA_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY", ""),
        )
    if provider == "qwen":
        return OpenAICompatibleProvider(
            provider="qwen",
            model=os.getenv("SERA_LLM_MODEL", "qwen-plus"),
            base_url=os.getenv("SERA_LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            api_key=os.getenv("SERA_LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY", ""),
        )
    return MockLLMProvider()

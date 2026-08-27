"""Provider construction from credential-free experiment configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sera_edit.providers.base import LLMProvider
from sera_edit.providers.deepseek_provider import DeepSeekProvider
from sera_edit.providers.mock_provider import BenchmarkMockProvider
from sera_edit.providers.openai_provider import OpenAIProvider
from sera_edit.providers.qwen_provider import QwenProvider


def create_provider(config: dict[str, Any], benchmark_root: Path) -> LLMProvider:
    """Create one configured provider without accepting inline API keys."""

    if "api_key" in config:
        raise ValueError("API keys must be supplied through api_key_env, never inline configuration")
    name = str(config.get("provider", "")).strip().lower()
    if name == "mock":
        return BenchmarkMockProvider(benchmark_root)
    classes = {"openai": OpenAIProvider, "deepseek": DeepSeekProvider, "qwen": QwenProvider}
    if name not in classes:
        raise ValueError(f"unsupported provider: {name}")
    kwargs = {
        key: config[key]
        for key in (
            "model",
            "base_url",
            "api_key_env",
            "timeout_seconds",
            "input_cost_per_million",
            "output_cost_per_million",
            "supports_structured_outputs",
        )
        if key in config
    }
    return classes[name](**kwargs)

"""Small provider interfaces for schema-constrained Sera agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class LLMCallResult:
    """Result from one provider call."""

    provider: str
    model: str
    text: str
    used_live_provider: bool
    latency_ms: float
    error: str = ""
    raw_response: dict[str, Any] | None = None


class BaseLLMProvider(Protocol):
    """Provider contract used by the score editing agent."""

    provider: str
    model: str

    def available(self) -> bool:
        """Return whether the provider has enough configuration for a live call."""

    def complete_json(self, system_prompt: str, user_prompt: str) -> LLMCallResult:
        """Return JSON text or an error-bearing fallback result."""

"""Provider-neutral response contracts with cost and latency evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ProviderResponse:
    """One raw and parsed model response plus reproducibility metadata."""

    raw_text: str
    parsed_output: Any
    provider: str
    model: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    request_id: str | None = None
    finish_reason: str | None = None
    error: str | None = None
    cached: bool = False
    retry_count: int = 0
    request_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class LLMProvider(Protocol):
    """Common provider interface for all three experimental conditions."""

    def generate(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Generate one response without exposing credentials in metadata."""


@dataclass(slots=True)
class ProviderRequestError(RuntimeError):
    """A sanitized provider failure with retry guidance."""

    message: str
    retryable: bool = False
    status_code: int | None = None
    retry_after_seconds: float | None = None

    def __str__(self) -> str:
        return self.message

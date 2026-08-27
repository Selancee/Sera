"""Cache, retry, rate, and cost controls shared by experiment providers."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

from sera_edit.providers.base import LLMProvider, ProviderRequestError, ProviderResponse


class BudgetExceeded(RuntimeError):
    """Raised before a request when the configured cost budget cannot cover it."""


class RateLimiter:
    """Thread-safe fixed-interval request limiter."""

    def __init__(
        self,
        requests_per_minute: float | None,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.interval = 0.0 if not requests_per_minute else 60.0 / float(requests_per_minute)
        self.clock = clock
        self.sleeper = sleeper
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        """Wait until the next configured request slot."""

        if self.interval <= 0:
            return
        with self._lock:
            now = self.clock()
            delay = max(0.0, self._next_allowed - now)
            if delay:
                self.sleeper(delay)
                now = self.clock()
            self._next_allowed = max(now, self._next_allowed) + self.interval


class BudgetLedger:
    """Reserve conservative request cost before allowing concurrent provider calls."""

    def __init__(
        self,
        limit_usd: float | None,
        input_cost_per_million: float | None,
        output_cost_per_million: float | None,
    ) -> None:
        self.limit_usd = None if limit_usd is None else float(limit_usd)
        self.input_cost = input_cost_per_million
        self.output_cost = output_cost_per_million
        self.spent_usd = 0.0
        self.reserved_usd = 0.0
        self._lock = threading.Lock()

    def estimate(self, messages: list[dict[str, str]], max_tokens: int | None) -> float:
        """Estimate cost conservatively from UTF-8 text size and the output cap."""

        if self.input_cost is None or self.output_cost is None:
            return 0.0
        approximate_input_tokens = max(1, sum(len(item.get("content", "")) for item in messages) // 4)
        output_tokens = max_tokens if max_tokens is not None else 4096
        return (
            approximate_input_tokens * float(self.input_cost)
            + output_tokens * float(self.output_cost)
        ) / 1_000_000

    def reserve(self, estimate_usd: float) -> float:
        """Reserve one request or raise before it can exceed the hard budget."""

        amount = max(0.0, float(estimate_usd))
        with self._lock:
            if self.limit_usd is not None and self.spent_usd + self.reserved_usd + amount > self.limit_usd + 1e-12:
                raise BudgetExceeded(
                    f"cost budget exhausted: spent=${self.spent_usd:.6f}, reserved=${self.reserved_usd:.6f}, "
                    f"next=${amount:.6f}, limit=${self.limit_usd:.6f}"
                )
            self.reserved_usd += amount
        return amount

    def settle(self, reservation_usd: float, actual_usd: float | None) -> None:
        """Replace one reservation with actual or conservative estimated cost."""

        actual = reservation_usd if actual_usd is None else max(0.0, float(actual_usd))
        with self._lock:
            self.reserved_usd = max(0.0, self.reserved_usd - reservation_usd)
            self.spent_usd += actual


class ControlledProvider:
    """Add deterministic caching and bounded operational controls to any provider."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        cache_root: Path,
        cache_enabled: bool,
        max_retries: int,
        retry_backoff_seconds: float,
        requests_per_minute: float | None,
        budget: BudgetLedger,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.inner = provider
        self.provider = str(getattr(provider, "provider", "unknown"))
        self.model = str(getattr(provider, "model", "unknown"))
        self.cache_root = cache_root
        self.cache_enabled = bool(cache_enabled)
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))
        self.rate_limiter = RateLimiter(requests_per_minute, sleeper=sleeper)
        self.budget = budget
        self.sleeper = sleeper

    def _request_hash(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any] | None,
        temperature: float,
        seed: int | None,
        max_tokens: int | None,
    ) -> str:
        payload = {
            "provider": self.provider,
            "model": self.model,
            "messages": messages,
            "response_schema": response_schema,
            "temperature": temperature,
            "seed": seed,
            "max_tokens": max_tokens,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def _cache_path(self, request_hash: str) -> Path:
        safe_provider = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.provider)
        safe_model = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.model)
        return self.cache_root / safe_provider / safe_model / f"{request_hash}.json"

    def generate(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Return a cached response or issue a bounded provider request."""

        request_hash = self._request_hash(messages, response_schema, temperature, seed, max_tokens)
        cache_path = self._cache_path(request_hash)
        if self.cache_enabled and cache_path.exists():
            response = ProviderResponse(**json.loads(cache_path.read_text(encoding="utf-8")))
            response.cached = True
            response.request_hash = request_hash
            return response
        estimate = self.budget.estimate(messages, max_tokens)
        for attempt in range(self.max_retries + 1):
            reservation = self.budget.reserve(estimate)
            self.rate_limiter.wait()
            try:
                response = self.inner.generate(
                    messages,
                    response_schema=response_schema,
                    temperature=temperature,
                    seed=seed,
                    max_tokens=max_tokens,
                    metadata=metadata,
                )
            except ProviderRequestError as exc:
                self.budget.settle(reservation, None)
                if not exc.retryable or attempt >= self.max_retries:
                    raise
                delay = exc.retry_after_seconds
                if delay is None:
                    delay = self.retry_backoff_seconds * (2**attempt)
                self.sleeper(min(60.0, max(0.0, delay)))
                continue
            except Exception:
                self.budget.settle(reservation, None)
                raise
            self.budget.settle(reservation, response.estimated_cost)
            response.cached = False
            response.retry_count = attempt
            response.request_hash = request_hash
            if self.cache_enabled:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(response.as_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return response
        raise AssertionError("unreachable retry loop")

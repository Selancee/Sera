"""Deterministic benchmark-fixture provider for non-formal smoke tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.score_document_service import score_document_to_musicxml
from sera_edit.providers.base import ProviderResponse


class BenchmarkMockProvider:
    """Return cached gold fixtures; results are never formal model evidence."""

    provider = "mock"
    model = "benchmark-fixture-v2-roundtrip"

    def __init__(self, benchmark_root: Path) -> None:
        self.benchmark_root = benchmark_root

    def generate(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        del messages, response_schema, temperature, seed, max_tokens
        info = dict(metadata or {})
        task = dict(info["task"])
        condition = str(info["condition"])
        if task["expected_status"] == "refuse":
            parsed: Any = {"refusal": True, "reason": task["unsupported_reason"]}
            raw = json.dumps(parsed, ensure_ascii=False)
        elif condition == "full_rewrite":
            expected = Path(str(task["expected_output_path"]))
            expected_score = json.loads((self.benchmark_root / expected).read_text(encoding="utf-8"))
            raw = score_document_to_musicxml(expected_score)
            parsed = {"musicxml": raw}
        else:
            parsed = json.loads((self.benchmark_root / task["gold_patch_path"]).read_text(encoding="utf-8"))
            raw = json.dumps(parsed, ensure_ascii=False)
        return ProviderResponse(
            raw_text=raw,
            parsed_output=parsed,
            provider=self.provider,
            model=self.model,
            latency_ms=0.0,
            input_tokens=0,
            output_tokens=0,
            estimated_cost=0.0,
            request_id=f"mock:{task['task_id']}:{condition}",
            finish_reason="fixture",
        )

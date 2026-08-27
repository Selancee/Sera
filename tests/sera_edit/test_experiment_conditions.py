from __future__ import annotations

import json
from pathlib import Path

from evaluation.conditions.sera_edit_conditions import run_condition
from evaluation.metrics.sera_edit_metrics import compute_task_metrics
from sera_edit.providers.base import ProviderResponse
from sera_edit.providers.mock_provider import BenchmarkMockProvider


def _assets(task_id: str) -> tuple[dict, dict, BenchmarkMockProvider]:
    root = Path(__file__).resolve().parents[2] / "benchmark"
    task = json.loads((root / "tasks" / "batch1" / f"{task_id}.json").read_text(encoding="utf-8"))
    score = json.loads((root / "source_scores" / f"{task['score_id']}.score.json").read_text(encoding="utf-8"))
    return task, score, BenchmarkMockProvider(root)


def test_three_conditions_keep_baseline_boundaries() -> None:
    task, score, provider = _assets("pitch_001")
    rewrite = run_condition("full_rewrite", task, score, provider)
    patch_only = run_condition("patch_only", task, score, provider)
    full = run_condition("sera_full", task, score, provider)
    assert rewrite.patch is None and rewrite.patch_parsed is None
    assert rewrite.provider_response.model == "benchmark-fixture-v2-roundtrip"
    assert patch_only.validation_report["status"] == "basic_apply_only"
    assert full.validation_report["status"] == "valid"
    assert patch_only.score_document is not None
    assert full.score_document is not None


def test_mock_provider_refusal_is_explicit() -> None:
    task, score, provider = _assets("conflict_001")
    for condition in ("full_rewrite", "patch_only", "sera_full"):
        outcome = run_condition(condition, task, score, provider)
        assert outcome.refusal is True
        assert outcome.score_document is None


def test_correct_refusal_is_not_scored_as_invalid_musicxml() -> None:
    task, score, provider = _assets("conflict_001")
    outcome = run_condition("sera_full", task, score, provider)
    metrics = compute_task_metrics(task, score, outcome, None)
    assert metrics["task_success"] == 1
    assert metrics["musicxml_validity"] == ""
    assert metrics["non_target_preservation"] == 1.0
    assert metrics["operation_minimality"] == 1.0


class _RepairSequenceProvider:
    provider = "test"
    model = "repair-sequence"

    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.calls = 0

    def generate(self, messages, response_schema=None, temperature=0.0, seed=None, max_tokens=None, metadata=None):
        del messages, response_schema, temperature, seed, max_tokens, metadata
        payload = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return ProviderResponse(
            raw_text=json.dumps(payload),
            parsed_output=payload,
            provider=self.provider,
            model=self.model,
            latency_ms=2.0,
            input_tokens=5,
            output_tokens=10,
            estimated_cost=0.1,
            request_id=f"repair-{self.calls}",
        )


def test_sera_full_deterministic_repair_is_bounded_and_traced() -> None:
    task, score, _ = _assets("pitch_001")
    root = Path(__file__).resolve().parents[2] / "benchmark"
    gold = json.loads((root / task["gold_patch_path"]).read_text(encoding="utf-8"))
    gold.pop("schema_version")
    provider = _RepairSequenceProvider([gold])
    outcome = run_condition("sera_full", task, score, provider, max_repair_attempts=2)
    assert outcome.score_document is not None
    assert outcome.repair_attempted is True
    assert outcome.repair_success is True
    assert outcome.repair_attempt_count == 0
    assert provider.calls == 1
    assert outcome.repair_trace[0]["kind"] == "deterministic"


def test_sera_full_llm_repair_cost_is_counted_without_leaking_to_patch_only() -> None:
    task, score, _ = _assets("pitch_001")
    root = Path(__file__).resolve().parents[2] / "benchmark"
    gold = json.loads((root / task["gold_patch_path"]).read_text(encoding="utf-8"))
    full_provider = _RepairSequenceProvider([{"invalid": True}, gold])
    outcome = run_condition("sera_full", task, score, full_provider, max_repair_attempts=2)
    expected = json.loads((root / task["expected_output_path"]).read_text(encoding="utf-8"))
    metrics = compute_task_metrics(task, score, outcome, expected)
    assert outcome.score_document is not None
    assert outcome.repair_attempt_count == 1
    assert metrics["input_tokens"] == 10
    assert metrics["output_tokens"] == 20
    assert metrics["estimated_cost"] == 0.2
    assert metrics["repair_added_cost"] == 0.1

    baseline_provider = _RepairSequenceProvider([{"invalid": True}, gold])
    baseline = run_condition("patch_only", task, score, baseline_provider, max_repair_attempts=2)
    assert baseline.score_document is None
    assert baseline_provider.calls == 1
    assert baseline.repair_attempt_count == 0

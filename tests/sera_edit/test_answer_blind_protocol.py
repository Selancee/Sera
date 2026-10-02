from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from evaluation.benchmark_io import load_task
from evaluation.conditions.sera_edit_conditions import run_condition
from evaluation.runners.runtime_controls import BudgetExceeded, BudgetLedger
from sera_edit.generation.prompts import build_condition_messages, build_repair_messages
from sera_edit.providers.base import ProviderResponse

ROOT = Path(__file__).resolve().parents[2]


def test_all_120_tasks_are_answer_blind_in_generation_and_repair():
    benchmark = ROOT / "benchmark"
    split = json.loads((benchmark / "splits/core.json").read_text())
    for task_id in split["task_ids"]:
        task = load_task(benchmark, task_id, "core")
        score = json.loads((benchmark / "source_scores" / f"{task['score_id']}.score.json").read_text())
        poisoned = copy.deepcopy(task)
        for field in ("expected_status", "expected_constraints", "unsupported_reason", "gold_patch_path", "expected_output_path", "task_id"):
            poisoned[field] = "ANSWER_SENTINEL"
        outputs = {}
        for condition in ("full_rewrite", "patch_only", "sera_full"):
            actual = build_condition_messages(condition, task, score, protocol="answer_blind_v2")
            assert actual == build_condition_messages(condition, poisoned, score, protocol="answer_blind_v2")
            assert "ANSWER_SENTINEL" not in json.dumps(actual)
            outputs[condition] = actual
        assert outputs["patch_only"] == outputs["sera_full"]
        assert build_repair_messages(task, score, {}, [], attempt=1, protocol="answer_blind_v2") == build_repair_messages(poisoned, score, {}, [], attempt=1, protocol="answer_blind_v2")


def test_model_cannot_remove_user_protected_scope():
    task = load_task(ROOT / "benchmark", "dynamics_001")
    score = json.loads((ROOT / "benchmark/source_scores/score_001.score.json").read_text())
    patch = json.loads((ROOT / "benchmark" / task["gold_patch_path"]).read_text())
    patch["protected_scope"] = {}

    class Provider:
        provider = "test"
        def generate(self, messages, **kwargs):
            assert "task" not in kwargs["metadata"]
            return ProviderResponse(json.dumps(patch), patch, "test", "test", 0)

    before = copy.deepcopy(score)
    outcome = run_condition("sera_full", task, score, Provider(), prompt_protocol="answer_blind_v2", max_repair_attempts=0)
    assert outcome.score_document is None
    assert "E11" in outcome.error_codes
    assert score == before


def test_budget_survives_interruption_and_resume(tmp_path):
    path = tmp_path / "ledger.json"
    first = BudgetLedger(1, 1, 1, state_path=path)
    first.reserve(.6)
    resumed = BudgetLedger(1, 1, 1, state_path=path)
    with pytest.raises(BudgetExceeded):
        resumed.reserve(.5)
    assert resumed.spent_usd == .6
    assert resumed.estimate([{"content": "谱" * 1000}], 100) >= .0031

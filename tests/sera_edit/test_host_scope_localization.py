from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from sera_edit.execution.transaction import PatchTransaction
from sera_edit.generation.instruction_scope import (
    explicit_instruction_measures,
    explicit_instruction_staffs,
    resolve_instruction_target_scope,
)
from sera_edit.generation.llm_patch_generator import generate_llm_patch
from sera_edit.generation.rule_patch_generator import generate_rule_patch
from sera_edit.providers.base import ProviderResponse


ROOT = Path(__file__).resolve().parents[2]


def _score_007() -> dict[str, Any]:
    return json.loads((ROOT / "benchmark/source_scores/score_007.score.json").read_text(encoding="utf-8"))


def _compound_001() -> dict[str, Any]:
    return json.loads((ROOT / "benchmark/tasks/batch2/compound_001.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", ["en", "zh"])
def test_compound_001_uses_instruction_measure_inside_larger_host_selection(language: str) -> None:
    score = _score_007()
    instruction = _compound_001()[f"instruction_{language}"]

    generated = generate_rule_patch(
        score,
        instruction,
        {"measures": [2, 3], "staffs": [1]},
        {"staffs": [2]},
    )

    assert generated.status == "generated"
    assert generated.patch is not None
    assert generated.patch["target_scope"]["measures"] == [2]
    assert generated.patch["provenance"]["scope_resolution"] == "narrowed_to_explicit_instruction_scope"
    assert generated.patch["provenance"]["excluded_host_scope"]["measures"] == [3]
    assert [operation["selector"]["event_ids"] for operation in generated.patch["operations"]] == [
        ["s007_m2_rh_3", "s007_m2_rh_4"],
        ["s007_m2_rh_4"],
    ]

    preview = PatchTransaction().execute(score, generated.patch, dry_run=True)
    assert preview.report.status == "valid"
    assert {item["event_id"] for item in preview.diff["changed"]} == {
        "s007_m2_rh_3",
        "s007_m2_rh_4",
    }
    assert not any(item["event_id"].startswith("s007_m3_") for item in preview.diff["changed"])


def test_instruction_scope_parser_does_not_confuse_semitone_number_with_measure() -> None:
    instruction = "Transpose the final two notes of measure 2 staff 1 up by 1 semitone."

    assert explicit_instruction_measures(instruction) == (2,)
    assert explicit_instruction_staffs(instruction) == ("right_hand",)


def test_instruction_scope_never_broadens_outside_host_selection() -> None:
    score = _score_007()

    resolution = resolve_instruction_target_scope(
        score,
        "Transpose measure 2 staff 1 up a semitone.",
        {"measures": [3], "staffs": [1]},
    )

    assert resolution.valid is False
    assert resolution.status == "instruction_scope_outside_host_selection"
    assert "unselected measure" in str(resolution.reason)


def test_instruction_scope_filters_stable_event_ids_from_adjacent_measure() -> None:
    score = _score_007()

    resolution = resolve_instruction_target_scope(
        score,
        "Change every selected note in measure 2 staff 1 to forte.",
        {
            "measures": [2, 3],
            "staffs": [1],
            "event_ids": ["s007_m2_rh_4", "s007_m3_rh_1"],
        },
    )

    assert resolution.valid is True
    assert resolution.effective_scope is not None
    assert resolution.effective_scope.event_ids == frozenset({"s007_m2_rh_4"})
    assert resolution.effective_scope.measures == frozenset({2})


def test_live_llm_receives_only_instruction_measure_from_oversized_host_selection() -> None:
    score = _score_007()

    class ApplyAllProvider:
        provider = "test-live"
        model = "test-live-model"

        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
            self.calls.append({"messages": messages, **kwargs})
            return ProviderResponse(
                raw_text="{}",
                parsed_output={
                    "status": "patch",
                    "reason": "",
                    "operations": [
                        {
                            "type": "set_dynamic",
                            "apply_to_all_selected": True,
                            "event_ids": [],
                            "semitones": 0,
                            "pitch": "",
                            "dynamic": "f",
                            "articulations": [],
                        }
                    ],
                },
                provider=self.provider,
                model=self.model,
                latency_ms=1.0,
                input_tokens=10,
                output_tokens=10,
                request_id="scope-test",
                finish_reason="completed",
            )

    provider = ApplyAllProvider()
    generated = generate_llm_patch(
        score,
        "Set every note in measure 2 staff 1 to forte.",
        {"measures": [2, 3], "staffs": [1]},
        {"staffs": [2]},
        provider,
    )

    assert generated.status == "generated"
    assert generated.patch is not None
    assert generated.patch["target_scope"]["measures"] == [2]
    assert generated.patch["provenance"]["excluded_host_scope"]["measures"] == [3]
    selected_ids = generated.patch["operations"][0]["selector"]["event_ids"]
    assert selected_ids
    assert all(event_id.startswith("s007_m2_rh_") for event_id in selected_ids)
    prompt_payload = json.loads(provider.calls[0]["messages"][1]["content"])
    assert prompt_payload["target_scope"]["measures"] == [2]
    assert all(event_id.startswith("s007_m2_rh_") for event_id in prompt_payload["editable_event_ids"])


def test_generate_preview_api_protects_measure_3_for_compound_001(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERA_LLM_PROVIDER", "local_rule")
    task = _compound_001()

    response = TestClient(app).post(
        "/sera-edit/generate-preview",
        json={
            "score_document": _score_007(),
            "instruction": task["instruction_en"],
            "target_scope": {"measures": [2, 3], "staffs": [1]},
            "protected_scope": {"staffs": [2]},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["patch"]["target_scope"]["measures"] == [2]
    assert payload["preview"]["validation_report"]["status"] == "valid"
    changed = payload["preview"]["diff"]["changed"]
    assert {item["event_id"] for item in changed} == {"s007_m2_rh_3", "s007_m2_rh_4"}
    assert payload["preview"]["validation_report"]["checks"]["protected_scope"]["checks"][
        "unexpected_changed_elements"
    ] == 0

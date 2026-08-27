from __future__ import annotations

from typing import Any

from sera_edit.execution.transaction import PatchTransaction
from sera_edit.generation.llm_patch_generator import (
    generate_llm_patch,
    generate_patch_with_runtime,
    llm_patch_proposal_schema,
)
from sera_edit.providers.base import ProviderResponse
from sera_edit.providers.runtime import LLMRuntimeSettings


class _ProposalProvider:
    provider = "test-live"
    model = "test-live-model"

    def __init__(self, proposal: dict[str, Any]) -> None:
        self.proposal = proposal
        self.calls: list[dict[str, Any]] = []

    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        self.calls.append({"messages": messages, **kwargs})
        return ProviderResponse(
            raw_text="{}",
            parsed_output=self.proposal,
            provider=self.provider,
            model=self.model,
            latency_ms=12.5,
            input_tokens=100,
            output_tokens=40,
            request_id="request-live-1",
            finish_reason="completed",
        )


class _SequenceProvider(_ProposalProvider):
    def __init__(self, proposals: list[Any]) -> None:
        super().__init__({})
        self.proposals = proposals

    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        proposal = self.proposals[len(self.calls)]
        self.calls.append({"messages": messages, **kwargs})
        return ProviderResponse(
            raw_text="not-json" if proposal is None else "{}",
            parsed_output=proposal,
            provider=self.provider,
            model=self.model,
            latency_ms=12.5,
            input_tokens=100,
            output_tokens=40,
            request_id=f"request-live-{len(self.calls)}",
            finish_reason="completed",
        )


def _proposal(*, event_ids: list[str] | None = None, apply_all: bool = True) -> dict[str, Any]:
    return {
        "status": "patch",
        "reason": "",
        "operations": [
            {
                "type": "transpose",
                "apply_to_all_selected": apply_all,
                "event_ids": event_ids or [],
                "semitones": 2,
                "pitch": "",
                "dynamic": "",
                "articulations": [],
            }
        ],
    }


def test_live_generator_builds_server_owned_patch_and_transaction(two_staff_score: dict) -> None:
    provider = _ProposalProvider(_proposal())

    generated = generate_llm_patch(
        two_staff_score,
        "Transpose the upper staff up by a major second.",
        {"measures": [1], "staffs": [1]},
        {"staffs": [2]},
        provider,
    )

    assert generated.status == "generated"
    assert generated.patch is not None
    operation = generated.patch["operations"][0]
    assert operation["type"] == "transpose"
    assert operation["selector"]["event_ids"] == ["m1_rh_1", "m1_rh_2", "m1_rh_3", "m1_rh_4"]
    assert generated.patch["target_scope"]["staffs"] == ["right_hand"]
    assert generated.patch["protected_scope"]["staffs"] == ["left_hand"]
    assert generated.patch["provenance"]["provider"] == "test-live"
    assert "score_patch_schema" not in provider.calls[0]["messages"][1]["content"]
    assert provider.calls[0]["response_schema"] == llm_patch_proposal_schema()
    assert provider.calls[0]["metadata"] == {"thinking": "disabled"}

    preview = PatchTransaction().execute(two_staff_score, generated.patch, dry_run=True)
    assert preview.report.status == "valid"
    proposed = preview.as_dict()["proposed_score_document"]
    assert proposed is not None
    assert proposed["measures"][0]["events"][0]["pitch"] == "D4"


def test_live_generator_rejects_hallucinated_event_id(two_staff_score: dict) -> None:
    provider = _ProposalProvider(_proposal(event_ids=["invented_event"], apply_all=False))

    generated = generate_llm_patch(
        two_staff_score,
        "Transpose one selected note.",
        {"measures": [1], "staffs": [1]},
        {"staffs": [2]},
        provider,
    )

    assert generated.status == "unsupported"
    assert generated.patch is None
    assert "event ID" in str(generated.reason)


def test_live_generator_preserves_explicit_model_refusal(two_staff_score: dict) -> None:
    provider = _ProposalProvider(
        {"status": "refusal", "reason": "The request requires inserting measures.", "operations": []}
    )

    generated = generate_llm_patch(
        two_staff_score,
        "Insert four new measures.",
        {"measures": [1]},
        {},
        provider,
    )

    assert generated.status == "refused"
    assert generated.patch is None
    assert "inserting measures" in str(generated.reason)


def test_live_generator_repairs_single_operation_object_without_second_request(two_staff_score: dict) -> None:
    proposal = _proposal()
    proposal["operations"] = proposal["operations"][0]
    provider = _ProposalProvider(proposal)

    generated = generate_llm_patch(
        two_staff_score,
        "Transpose the upper staff up by a major second.",
        {"measures": [1], "staffs": [1]},
        {"staffs": [2]},
        provider,
    )

    assert generated.status == "generated"
    assert generated.repair_strategy == "deterministic"
    assert generated.deterministic_repairs == ("wrapped_single_operation_in_array",)
    assert generated.generation_attempts == 1
    assert len(provider.calls) == 1


def test_live_generator_requests_one_bounded_repair_for_malformed_output(two_staff_score: dict) -> None:
    provider = _SequenceProvider([None, _proposal()])

    generated = generate_llm_patch(
        two_staff_score,
        "Transpose the upper staff up by a major second.",
        {"measures": [1], "staffs": [1]},
        {"staffs": [2]},
        provider,
    )

    assert generated.status == "generated"
    assert generated.repair_strategy == "llm"
    assert generated.generation_attempts == 2
    assert len(provider.calls) == 2
    assert "server_error" in provider.calls[1]["messages"][1]["content"]
    assert provider.calls[1]["metadata"] == {"thinking": "disabled"}


def test_interactive_runtime_compiles_exact_dynamic_edit_before_live_llm(two_staff_score: dict) -> None:
    provider = _ProposalProvider(_proposal())
    settings = LLMRuntimeSettings(
        provider="deepseek",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com/v1",
        api_key_env="SERA_LLM_API_KEY",
        configured=True,
        available=True,
        transport="chat_completions",
        fallback_local=True,
        timeout_seconds=90.0,
        max_output_tokens=4000,
        reasoning_effort="medium",
        store=False,
        supports_structured_outputs=False,
        input_cost_per_million=None,
        output_cost_per_million=None,
        config_file="test.env",
        reason="ready",
    )

    payload = generate_patch_with_runtime(
        two_staff_score,
        "Change only the third note in measure 1 to forte, preserving pitch and duration.",
        {"measures": [1], "staffs": [1], "event_ids": ["m1_rh_3"]},
        {"staffs": [2]},
        settings=settings,
        provider=provider,
    )

    assert payload["status"] == "generated"
    assert payload["generator"]["provider"] == "local_rule"
    assert payload["generator"]["routing"] == "local_first"
    assert payload["generator"]["requested_provider"] == "deepseek"
    assert payload["patch"]["operations"] == [
        {
            "operation_id": "op_001",
            "type": "set_dynamic",
            "selector": {"event_ids": ["m1_rh_3"]},
            "arguments": {"dynamic": "f"},
            "preconditions": [],
            "expected_change_count": 1,
        }
    ]
    assert provider.calls == []


def test_interactive_runtime_compiles_key_signature_edit_before_live_llm(two_staff_score: dict) -> None:
    provider = _ProposalProvider(_proposal())
    settings = LLMRuntimeSettings(
        provider="deepseek",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com/v1",
        api_key_env="SERA_LLM_API_KEY",
        configured=True,
        available=True,
        transport="chat_completions",
        fallback_local=True,
        timeout_seconds=90.0,
        max_output_tokens=4000,
        reasoning_effort="medium",
        store=False,
        supports_structured_outputs=False,
        input_cost_per_million=None,
        output_cost_per_million=None,
        config_file="test.env",
        reason="ready",
    )

    payload = generate_patch_with_runtime(
        two_staff_score,
        "Change the score key signature to G major without transposing notes.",
        {"whole_score": True},
        {},
        settings=settings,
        provider=provider,
    )

    assert payload["status"] == "generated"
    assert payload["generator"]["routing"] == "local_first"
    assert payload["patch"]["operations"][0]["type"] == "change_key_signature"
    assert payload["patch"]["operations"][0]["arguments"] == {"key": "G major"}
    assert provider.calls == []


def test_interactive_runtime_promotes_partial_host_scope_for_chinese_key_edit(two_staff_score: dict) -> None:
    provider = _ProposalProvider(_proposal())
    settings = LLMRuntimeSettings(
        provider="deepseek",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com/v1",
        api_key_env="SERA_LLM_API_KEY",
        configured=True,
        available=True,
        transport="chat_completions",
        fallback_local=True,
        timeout_seconds=90.0,
        max_output_tokens=4000,
        reasoning_effort="medium",
        store=False,
        supports_structured_outputs=False,
        input_cost_per_million=None,
        output_cost_per_million=None,
        config_file="test.env",
        reason="ready",
    )

    payload = generate_patch_with_runtime(
        two_staff_score,
        "将调号改为G major，但不要移调音符。",
        {"measures": [1, 2]},
        {},
        settings=settings,
        provider=provider,
    )

    assert payload["status"] == "generated"
    assert payload["generator"]["provider"] == "local_rule"
    assert payload["generator"]["routing"] == "local_first"
    assert payload["generator"]["scope_resolution"] == "promoted_to_whole_score_for_global_key_signature"
    assert payload["patch"]["target_scope"]["whole_score"] is True
    assert payload["patch"]["operations"][0]["arguments"] == {"key": "G major"}
    assert provider.calls == []

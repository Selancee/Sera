"""Separated implementations of Full Rewrite, Patch Only, and Sera Full."""

from __future__ import annotations

import copy
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from backend.services.score_document_service import musicxml_to_score_document, score_document_to_musicxml
from backend.validation.musicxml_validator import MusicXMLValidator
from sera_edit.domain.operations import OperationApplicationError, apply_patch_operation
from sera_edit.domain.score_patch import ScorePatch
from sera_edit.execution.patch_repair import deterministic_repair
from sera_edit.execution.transaction import PatchTransaction
from sera_edit.generation.prompts import build_condition_messages, build_repair_messages
from sera_edit.generation.response_parser import extract_musicxml, parse_json_object
from sera_edit.providers.base import LLMProvider, ProviderResponse
from sera_edit.validation.schema_validator import validate_patch_schema


@dataclass(slots=True)
class ConditionOutcome:
    """Normalized output shared by the evaluation runner."""

    condition: str
    refusal: bool
    score_document: dict[str, Any] | None
    musicxml: str | None
    patch: dict[str, Any] | None
    patch_parsed: bool | None
    validation_report: dict[str, Any]
    provider_response: ProviderResponse
    processing_latency_ms: float
    error_codes: list[str] = field(default_factory=list)
    error: str | None = None
    repair_attempted: bool = False
    repair_success: bool = False
    repair_attempt_count: int = 0
    repair_trace: list[dict[str, Any]] = field(default_factory=list)
    repair_responses: list[ProviderResponse] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["provider_response"] = self.provider_response.as_dict()
        payload["repair_responses"] = [response.as_dict() for response in self.repair_responses]
        return payload

    @property
    def all_provider_responses(self) -> list[ProviderResponse]:
        """Return initial and repair responses for complete cost accounting."""

        return [self.provider_response, *self.repair_responses]


def run_condition(
    condition: str,
    task: dict[str, Any],
    source_score: dict[str, Any],
    provider: LLMProvider,
    *,
    temperature: float = 0.0,
    seed: int | None = 42,
    max_tokens: int | None = None,
    max_repair_attempts: int = 2,
) -> ConditionOutcome:
    """Run exactly one condition without leaking Sera safeguards into baselines."""

    messages, response_schema = build_condition_messages(condition, task, source_score)
    response = provider.generate(
        messages,
        response_schema=response_schema,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
        metadata={"condition": condition, "task": task},
    )
    started = time.perf_counter()
    parsed = response.parsed_output
    if isinstance(parsed, dict) and parsed.get("refusal"):
        return ConditionOutcome(condition, True, None, None, None, None, {"status": "refused"}, response, (time.perf_counter() - started) * 1000)
    if condition == "full_rewrite":
        try:
            musicxml = extract_musicxml(response.raw_text)
            score = musicxml_to_score_document(musicxml, source="condition_a_full_rewrite")
            validation = MusicXMLValidator().validate_text(musicxml)
            return ConditionOutcome(
                condition, False, score, musicxml, None, None,
                {"status": "valid" if validation.valid else "invalid", "issues": list(validation.issues), "metrics": dict(validation.metrics)},
                response, (time.perf_counter() - started) * 1000,
                [] if validation.valid else ["E02"], None if validation.valid else "full rewrite MusicXML invalid",
            )
        except Exception as exc:  # noqa: BLE001 - baseline output may be arbitrarily malformed.
            return ConditionOutcome(condition, False, None, None, None, None, {"status": "invalid"}, response, (time.perf_counter() - started) * 1000, ["E01"], str(exc))
    initial_patch_parsed = isinstance(parsed, dict)
    if not isinstance(parsed, dict):
        if condition == "sera_full":
            parsed = parse_json_object(response.raw_text)
            initial_patch_parsed = isinstance(parsed, dict)
    if not isinstance(parsed, dict) and condition != "sera_full":
        return ConditionOutcome(condition, False, None, None, None, False, {"status": "invalid"}, response, (time.perf_counter() - started) * 1000, ["E03"], "patch output is not an object")
    if condition == "patch_only":
        schema = validate_patch_schema(parsed)
        if schema.errors:
            return ConditionOutcome(condition, False, None, None, parsed, True, schema.as_dict(), response, (time.perf_counter() - started) * 1000, [item.code for item in schema.errors], "patch schema invalid")
        try:
            patch = ScorePatch.from_dict(parsed)
            score = copy.deepcopy(source_score)
            for operation in patch.operations:
                score, _ = apply_patch_operation(score, operation, patch.target_scope)
            musicxml = score_document_to_musicxml(score)
            return ConditionOutcome(condition, False, score, musicxml, parsed, True, {"status": "basic_apply_only"}, response, (time.perf_counter() - started) * 1000)
        except OperationApplicationError as exc:
            return ConditionOutcome(condition, False, None, None, parsed, True, {"status": "invalid"}, response, (time.perf_counter() - started) * 1000, [exc.code], exc.message)

    # Condition C alone receives bounded repair. Baselines above remain untouched.
    repair_trace: list[dict[str, Any]] = []
    repair_responses: list[ProviderResponse] = []
    candidate: Any = parsed if isinstance(parsed, dict) else response.raw_text
    final_report: dict[str, Any] = {"status": "invalid", "errors": []}
    final_codes = ["E03"]
    final_error = "patch output is not an object"
    max_attempts = max(0, int(max_repair_attempts))
    for attempt in range(max_attempts + 1):
        if isinstance(candidate, dict) and candidate.get("refusal"):
            return ConditionOutcome(
                condition, True, None, None, None, initial_patch_parsed, {"status": "refused"}, response,
                (time.perf_counter() - started) * 1000, repair_attempted=bool(repair_trace),
                repair_success=bool(repair_responses), repair_attempt_count=len(repair_responses),
                repair_trace=repair_trace, repair_responses=repair_responses,
            )
        schema = validate_patch_schema(candidate)
        if schema.errors and isinstance(candidate, dict):
            deterministic = deterministic_repair(candidate)
            if deterministic.changes:
                candidate = deterministic.repaired
                repair_trace.append(
                    {
                        "kind": "deterministic",
                        "attempt": attempt,
                        "changes": list(deterministic.changes),
                        "valid_after_repair": deterministic.valid,
                    }
                )
                schema = validate_patch_schema(candidate)
        if not schema.errors:
            result = PatchTransaction().execute(source_score, candidate)
            final_report = result.report.as_dict()
            final_codes = [item.code for item in result.report.errors]
            final_error = result.rollback_reason or "patch transaction rejected"
            if result.committed:
                return ConditionOutcome(
                    condition, False, result.score_document, result.musicxml, candidate, initial_patch_parsed,
                    final_report, response, (time.perf_counter() - started) * 1000, [], None,
                    repair_attempted=bool(repair_trace or repair_responses),
                    repair_success=bool(repair_trace or repair_responses),
                    repair_attempt_count=len(repair_responses), repair_trace=repair_trace,
                    repair_responses=repair_responses,
                )
            if result.report.unsupported:
                break
        else:
            final_report = schema.as_dict()
            final_codes = [item.code for item in schema.errors]
            final_error = "patch schema invalid"
        if attempt >= max_attempts:
            break
        repair_messages, repair_schema = build_repair_messages(
            task,
            source_score,
            candidate,
            list(final_report.get("errors") or []),
            attempt=attempt + 1,
        )
        repair_response = provider.generate(
            repair_messages,
            response_schema=repair_schema,
            temperature=temperature,
            seed=seed,
            max_tokens=max_tokens,
            metadata={"condition": "sera_full_repair", "task": task, "repair_attempt": attempt + 1},
        )
        repair_responses.append(repair_response)
        candidate = repair_response.parsed_output
        if not isinstance(candidate, dict):
            candidate = parse_json_object(repair_response.raw_text) or repair_response.raw_text
        repair_trace.append(
            {
                "kind": "provider",
                "attempt": attempt + 1,
                "request_id": repair_response.request_id,
                "parsed": isinstance(candidate, dict),
            }
        )
    return ConditionOutcome(
        condition, False, None, None, candidate if isinstance(candidate, dict) else None, initial_patch_parsed,
        final_report, response, (time.perf_counter() - started) * 1000, final_codes, final_error,
        repair_attempted=bool(repair_trace or repair_responses), repair_success=False,
        repair_attempt_count=len(repair_responses), repair_trace=repair_trace,
        repair_responses=repair_responses,
    )

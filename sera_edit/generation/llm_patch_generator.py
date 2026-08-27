"""Live LLM planning constrained to server-owned, source-preserving ScorePatch operations."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from backend.services.score_document_service import normalize_score_document
from sera_edit.composer.intent_router import is_compositional_edit_instruction
from sera_edit.composer.pipeline import compose_with_runtime
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.domain.score_scope import ScoreScope
from sera_edit.generation.prompts import compact_score_context
from sera_edit.generation.instruction_scope import resolve_instruction_target_scope
from sera_edit.generation.rule_patch_generator import generate_rule_patch
from sera_edit.providers.base import LLMProvider, ProviderRequestError, ProviderResponse
from sera_edit.providers.runtime import LLMRuntimeSettings, create_runtime_provider, runtime_settings
from sera_edit.validation.schema_validator import validate_patch_schema


GenerationStatus = Literal["generated", "unsupported", "refused"]
ALLOWED_OPERATION_TYPES = ("transpose", "set_pitch", "set_dynamic", "set_articulation")
ALLOWED_DYNAMICS = {"ppp", "pp", "p", "mp", "mf", "f", "ff", "fff"}
ALLOWED_ARTICULATIONS = {"staccato", "accent", "tenuto"}
PITCH_PATTERN = re.compile(r"^[A-G](?:#|b)?[0-9]$")
PROMPT_VERSION = "sera_interactive_patch_v1.1"


@dataclass(frozen=True, slots=True)
class LLMPatchGenerationResult:
    status: GenerationStatus
    patch: dict[str, Any] | None = None
    reason: str | None = None
    matched_intents: tuple[str, ...] = field(default_factory=tuple)
    provider_response: ProviderResponse | None = None
    generation_attempts: int = 1
    repair_strategy: str = "none"
    deterministic_repairs: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        response = self.provider_response
        return {
            "status": self.status,
            "patch": self.patch,
            "reason": self.reason,
            "matched_intents": list(self.matched_intents),
            "generator": {
                "provider": response.provider if response else "unknown",
                "model": response.model if response else "unknown",
                "transport": "responses" if response and response.provider == "openai" else "chat_completions",
                "live": True,
                "formal_experiment_eligible": False,
                "prompt_version": PROMPT_VERSION,
                "latency_ms": round(response.latency_ms, 3) if response else None,
                "input_tokens": response.input_tokens if response else None,
                "output_tokens": response.output_tokens if response else None,
                "estimated_cost": response.estimated_cost if response else None,
                "request_id": response.request_id if response else None,
                "generation_attempts": self.generation_attempts,
                "repair_strategy": self.repair_strategy,
                "deterministic_repairs": list(self.deterministic_repairs),
            },
        }


def llm_patch_proposal_schema() -> dict[str, Any]:
    """Return the strict transport schema; the server constructs the final ScorePatch."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "reason", "operations"],
        "properties": {
            "status": {"type": "string", "enum": ["patch", "refusal"]},
            "reason": {"type": "string"},
            "operations": {
                "type": "array",
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "type",
                        "apply_to_all_selected",
                        "event_ids",
                        "semitones",
                        "pitch",
                        "dynamic",
                        "articulations",
                    ],
                    "properties": {
                        "type": {"type": "string", "enum": list(ALLOWED_OPERATION_TYPES)},
                        "apply_to_all_selected": {"type": "boolean"},
                        "event_ids": {
                            "type": "array",
                            "maxItems": 256,
                            "items": {"type": "string"},
                        },
                        "semitones": {"type": "integer", "minimum": -24, "maximum": 24},
                        "pitch": {"type": "string"},
                        "dynamic": {"type": "string", "enum": ["", *sorted(ALLOWED_DYNAMICS)]},
                        "articulations": {
                            "type": "array",
                            "maxItems": 3,
                            "items": {"type": "string", "enum": sorted(ALLOWED_ARTICULATIONS)},
                        },
                    },
                },
            },
        },
    }


def generate_llm_patch(
    score_document: dict[str, Any],
    instruction: str,
    target_scope_payload: dict[str, Any],
    protected_scope_payload: dict[str, Any] | None,
    provider: LLMProvider,
    *,
    max_output_tokens: int = 4000,
    max_repair_attempts: int = 1,
) -> LLMPatchGenerationResult:
    """Ask the LLM for a bounded plan and convert it into a server-owned ScorePatch."""

    score = normalize_score_document(score_document)
    requested_target_scope = ScoreScope.from_dict(target_scope_payload)
    protected_scope = ScoreScope.from_dict(protected_scope_payload)
    if requested_target_scope.empty:
        return LLMPatchGenerationResult("unsupported", reason="请先在宿主中选择至少一个小节或音符。")
    scope_resolution = resolve_instruction_target_scope(score, instruction, target_scope_payload)
    if not scope_resolution.valid or scope_resolution.effective_scope is None:
        return LLMPatchGenerationResult(
            "unsupported",
            reason=scope_resolution.reason or "指令指定的位置不在当前宿主选区内。",
        )
    target_scope = scope_resolution.effective_scope
    editable_contexts = [context for context in target_scope.select(score) if context.event.get("type") == "note"]
    if not editable_contexts:
        return LLMPatchGenerationResult("unsupported", reason="当前宿主选区中没有可编辑音符。")
    editable_ids = [context.event_id for context in editable_contexts]
    system_prompt = (
        "You are the planning model for Sera, a safe professional score-editing layer. "
        "Return only the supplied JSON schema. The operations field MUST always be a JSON array, even when there is "
        "only one operation. Never return MusicXML and never broaden the user's target scope. "
        "Use only event IDs in editable_event_ids. You may transpose, set exact pitch, set dynamic, or set "
        "staccato/accent/tenuto articulation. Refuse requests requiring insertion, deletion, duration or meter/key "
        "changes, ties/slurs, layout changes, whole-score regeneration, conflicting instructions, or unsupported "
        "musical semantics. Set apply_to_all_selected=true for operations covering every selected note. For unused "
        "fields use neutral values: semitones=0, pitch='', dynamic='', articulations=[]. "
        "For example, transposing every selected note by two semitones is "
        "{\"status\":\"patch\",\"reason\":\"\",\"operations\":[{\"type\":\"transpose\","
        "\"apply_to_all_selected\":true,\"event_ids\":[],\"semitones\":2,\"pitch\":\"\","
        "\"dynamic\":\"\",\"articulations\":[]}]}."
    )
    user_payload = {
        "instruction": instruction.strip(),
        "target_scope": target_scope.as_dict(),
        "protected_scope": protected_scope.as_dict(),
        "editable_event_ids": editable_ids,
        "score_context": compact_score_context(score, target_scope.as_dict()),
        "allowed_operations": list(ALLOWED_OPERATION_TYPES),
    }
    response = provider.generate(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))},
        ],
        response_schema=llm_patch_proposal_schema(),
        temperature=0.0,
        max_tokens=max_output_tokens,
        metadata={"thinking": "disabled"},
    )
    proposal, deterministic_repairs = _normalize_transport_proposal(response.parsed_output)
    responses = [response]
    repair_strategy = "deterministic" if deterministic_repairs else "none"
    if isinstance(proposal, dict) and proposal.get("status") == "refusal":
        return LLMPatchGenerationResult(
            "refused",
            reason=str(proposal.get("reason") or "LLM 判定该指令超出当前安全编辑范围。"),
            provider_response=response,
            deterministic_repairs=tuple(deterministic_repairs),
            repair_strategy=repair_strategy,
        )
    proposal_error = _proposal_error(proposal)
    operations: list[dict[str, Any]] = []
    if proposal_error is None:
        try:
            operations = _canonical_operations(proposal.get("operations"), editable_ids)
        except ValueError as exc:
            proposal_error = str(exc)
    if proposal_error is not None and max_repair_attempts > 0:
        repair_response = _request_proposal_repair(
            provider,
            instruction=instruction,
            target_scope=target_scope.as_dict(),
            protected_scope=protected_scope.as_dict(),
            editable_ids=editable_ids,
            score_context=user_payload["score_context"],
            candidate=response.parsed_output if response.parsed_output is not None else response.raw_text[:12_000],
            error=proposal_error,
            max_output_tokens=max_output_tokens,
        )
        responses.append(repair_response)
        response = repair_response
        proposal, repair_normalizations = _normalize_transport_proposal(response.parsed_output)
        deterministic_repairs.extend(repair_normalizations)
        repair_strategy = "llm+deterministic" if repair_normalizations else "llm"
        if isinstance(proposal, dict) and proposal.get("status") == "refusal":
            return LLMPatchGenerationResult(
                "refused",
                reason=str(proposal.get("reason") or "LLM 修复阶段判定该指令超出当前安全编辑范围。"),
                provider_response=response,
                generation_attempts=len(responses),
                repair_strategy=repair_strategy,
                deterministic_repairs=tuple(deterministic_repairs),
            )
        proposal_error = _proposal_error(proposal)
        if proposal_error is None:
            try:
                operations = _canonical_operations(proposal.get("operations"), editable_ids)
            except ValueError as exc:
                proposal_error = str(exc)
    if proposal_error is not None:
        return LLMPatchGenerationResult(
            "unsupported",
            reason=f"LLM 提案未通过服务器约束：{proposal_error}",
            provider_response=response,
            generation_attempts=len(responses),
            repair_strategy=repair_strategy,
            deterministic_repairs=tuple(deterministic_repairs),
        )
    if not operations:
        return LLMPatchGenerationResult(
            "unsupported",
            reason="LLM 提案没有包含可执行的局部修改。",
            provider_response=response,
            generation_attempts=len(responses),
            repair_strategy=repair_strategy,
            deterministic_repairs=tuple(deterministic_repairs),
        )
    fingerprint = score_fingerprint(score)
    patch_id = _patch_id(score, fingerprint, instruction, operations)
    operation_types = tuple(dict.fromkeys(str(operation["type"]) for operation in operations))
    expected_effects: list[dict[str, Any]] = [{"type": "preserve_duration"}]
    if not any(kind in {"transpose", "set_pitch"} for kind in operation_types):
        expected_effects.append({"type": "preserve_pitch"})
    patch = {
        "schema_version": "1.0.0",
        "patch_id": patch_id,
        "source_score_id": str(score.get("score_id", "")),
        "source_fingerprint": fingerprint,
        "instruction": instruction.strip(),
        "target_scope": target_scope.as_dict(),
        "protected_scope": protected_scope.as_dict(),
        "preconditions": [],
        "operations": operations,
        "expected_effects": expected_effects,
        "provenance": {
            "provider": response.provider,
            "model": response.model,
            "temperature": 0,
            "seed": None,
            "prompt_version": PROMPT_VERSION,
            "request_id": response.request_id,
            "latency_ms": round(response.latency_ms, 3),
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "formal_experiment_eligible": False,
            "generation_attempts": len(responses),
            "repair_strategy": repair_strategy,
            **scope_resolution.provenance(),
        },
    }
    validation = validate_patch_schema(patch)
    if validation.status == "invalid":
        return LLMPatchGenerationResult(
            "unsupported",
            reason="服务器构造的 ScorePatch 未通过 schema 校验。",
            provider_response=response,
            generation_attempts=len(responses),
            repair_strategy=repair_strategy,
            deterministic_repairs=tuple(deterministic_repairs),
        )
    return LLMPatchGenerationResult(
        "generated",
        patch=patch,
        matched_intents=operation_types,
        provider_response=response,
        generation_attempts=len(responses),
        repair_strategy=repair_strategy,
        deterministic_repairs=tuple(deterministic_repairs),
    )


def generate_patch_with_runtime(
    score_document: dict[str, Any],
    instruction: str,
    target_scope: dict[str, Any],
    protected_scope: dict[str, Any] | None = None,
    *,
    settings: LLMRuntimeSettings | None = None,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Use a live provider when ready and a visible local fallback otherwise."""

    resolved = settings or runtime_settings()
    # Compile exact event-level notation edits locally before paying the
    # latency and schema-failure cost of a remote planner. Broader edits still
    # use the configured model, preserving the existing live-LLM contract.
    # This is an interactive routing optimization only; formal benchmark
    # conditions continue to call their configured providers directly.
    local = generate_rule_patch(score_document, instruction, target_scope, protected_scope).as_dict()
    local_operations = (local.get("patch") or {}).get("operations") or []
    explicit_event_ids = target_scope.get("event_ids") if isinstance(target_scope, dict) else None
    exact_event_notation = bool(explicit_event_ids) and bool(local_operations) and all(
        operation.get("type") in {"set_dynamic", "set_articulation"}
        for operation in local_operations
    )
    requires_extended_operations = any(
        operation.get("type") not in ALLOWED_OPERATION_TYPES
        for operation in local_operations
    )
    deterministic_compound = len(local_operations) > 1
    local_first = (
        not resolved.available
        or local["status"] == "refused"
        or exact_event_notation
        or requires_extended_operations
        or deterministic_compound
    )
    if resolved.fallback_local and local["status"] in {"generated", "refused"} and local_first:
        local["generator"].update(
            {
                "live": False,
                "transport": "local",
                "requested_provider": resolved.provider,
                "routing": "local_first",
                "fallback_reason": "",
                "scope_resolution": (local.get("patch") or {}).get("provenance", {}).get(
                    "scope_resolution",
                    "requested_scope",
                ),
            }
        )
        local["provider_status"] = resolved.public_status()
        return local
    if is_compositional_edit_instruction(instruction):
        return _generate_composer_routed_patch(
            score_document,
            instruction,
            target_scope,
            protected_scope,
            settings=resolved,
            provider=provider,
        )
    live_provider = provider or create_runtime_provider(resolved)
    fallback_reason = ""
    if live_provider is not None:
        try:
            live_result = generate_llm_patch(
                score_document,
                instruction,
                target_scope,
                protected_scope,
                live_provider,
                max_output_tokens=resolved.max_output_tokens,
            )
            live_payload = live_result.as_dict()
            if live_result.status in {"generated", "refused"}:
                live_payload["provider_status"] = resolved.public_status()
                return live_payload
            fallback_reason = str(live_result.reason or "LLM output could not be converted into a safe patch.")
            if not resolved.fallback_local:
                live_payload["provider_status"] = resolved.public_status()
                return live_payload
        except (ProviderRequestError, ValueError) as exc:
            fallback_reason = str(exc)
            if not resolved.fallback_local:
                return {
                    "status": "unsupported",
                    "patch": None,
                    "reason": f"LLM API 调用失败：{fallback_reason}",
                    "matched_intents": [],
                    "generator": {
                        "provider": resolved.provider,
                        "model": resolved.model,
                        "transport": resolved.transport,
                        "live": False,
                        "formal_experiment_eligible": False,
                        "fallback_reason": fallback_reason,
                    },
                    "provider_status": resolved.public_status(),
                }
    else:
        fallback_reason = resolved.reason

    local["generator"].update(
        {
            "live": False,
            "transport": "local",
            "requested_provider": resolved.provider,
            "fallback_reason": fallback_reason,
        }
    )
    local["provider_status"] = resolved.public_status()
    if local["status"] == "unsupported" and resolved.configured and fallback_reason:
        local["reason"] = f"LLM API 未生成安全提案（{fallback_reason}）；本地规则也不支持该指令。"
    return local


def _generate_composer_routed_patch(
    score_document: dict[str, Any],
    instruction: str,
    target_scope: dict[str, Any],
    protected_scope: dict[str, Any] | None,
    *,
    settings: LLMRuntimeSettings,
    provider: LLMProvider | None,
) -> dict[str, Any]:
    """Compile the best reviewed Composer candidate into the patch channel."""

    composition = compose_with_runtime(
        score_document,
        instruction,
        target_scope,
        protected_scope,
        candidate_count=3,
        seed=42,
        settings=settings,
        provider=provider,
    )
    provider_status = composition.get("provider_status") or settings.public_status()
    candidates = [
        candidate
        for candidate in composition.get("candidates") or []
        if candidate.get("review", {}).get("status") == "valid" and candidate.get("patch")
    ]
    if composition.get("status") != "generated" or not candidates:
        return {
            "status": "unsupported",
            "patch": None,
            "reason": composition.get("reason") or "Composer 没有生成通过事务与保护范围检查的旋律候选。",
            "matched_intents": ["theory_guided_composition"],
            "generator": _composer_generator_evidence(composition, None),
            "provider_status": provider_status,
            "composition_evidence": _composer_composition_evidence(composition, None),
        }
    selected_id = composition.get("selected_candidate_id")
    selected = next(
        (candidate for candidate in candidates if candidate.get("candidate_id") == selected_id),
        candidates[0],
    )
    return {
        "status": "generated",
        "patch": selected["patch"],
        "reason": None,
        "matched_intents": ["theory_guided_composition", str(composition.get("plan", {}).get("mode") or "theory_variation")],
        "generator": _composer_generator_evidence(composition, selected),
        "provider_status": provider_status,
        "composition_evidence": _composer_composition_evidence(composition, selected),
    }


def _composer_composition_evidence(
    composition: dict[str, Any],
    selected: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return the bounded Composer trace for both accepted and rejected sets."""

    return {
        "plan": composition.get("plan"),
        "theory_context": composition.get("theory_context") or [],
        "style_knowledge": composition.get("style_knowledge"),
        "phrase_analysis": composition.get("phrase_analysis"),
        "search_summary": composition.get("search_summary") or {},
        "preference_profile": composition.get("preference_profile") or {},
        "comparison_id": composition.get("comparison_id"),
        "candidate_count": len(composition.get("candidates") or []),
        "selected_candidate_id": selected.get("candidate_id") if selected else None,
        "selected_review": selected.get("review") if selected else None,
        "failure_analysis": composition.get("failure_analysis"),
        "baseline_guarantees": composition.get("baseline_guarantees") or {},
    }


def _composer_generator_evidence(
    composition: dict[str, Any],
    selected: dict[str, Any] | None,
) -> dict[str, Any]:
    planner = composition.get("planner") or {}
    return {
        "provider": str(planner.get("provider") or "local_rule"),
        "model": str(planner.get("model") or "sera_composer_rules_v1"),
        "transport": "composer_pipeline",
        "live": planner.get("planner") == "live_llm",
        "formal_experiment_eligible": False,
        "prompt_version": str(planner.get("prompt_version") or "sera_composition_plan_v2.0"),
        "latency_ms": planner.get("latency_ms"),
        "input_tokens": planner.get("input_tokens"),
        "output_tokens": planner.get("output_tokens"),
        "request_id": planner.get("request_id"),
        "fallback_reason": planner.get("fallback_reason") or "",
        "generation_attempts": 1,
        "repair_strategy": "composer_candidate_selection",
        "deterministic_repairs": [],
        "composition_route": True,
        "candidate_count": len(composition.get("candidates") or []),
        "evaluated_candidate_count": int((composition.get("search_summary") or {}).get("evaluated") or 0),
        "search_width": int((composition.get("search_summary") or {}).get("search_width") or 0),
        "style_knowledge_version": (composition.get("style_knowledge") or {}).get("schema_version"),
        "preference_feedback_count": int((composition.get("preference_profile") or {}).get("feedback_count") or 0),
        "selected_candidate_id": selected.get("candidate_id") if selected else None,
        "selected_candidate_score": selected.get("review", {}).get("overall_score") if selected else None,
    }


def _normalize_transport_proposal(raw: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Repair only unambiguous transport-shape mistakes without inferring music."""

    if not isinstance(raw, dict):
        return None, []
    proposal = dict(raw)
    repairs: list[str] = []
    operations = proposal.get("operations")
    if isinstance(operations, dict):
        proposal["operations"] = [operations]
        repairs.append("wrapped_single_operation_in_array")
    if "status" not in proposal and isinstance(proposal.get("operations"), list):
        proposal["status"] = "patch"
        repairs.append("filled_patch_status")
    return proposal, repairs


def _proposal_error(proposal: dict[str, Any] | None) -> str | None:
    if not isinstance(proposal, dict):
        return "没有返回可解析的 JSON 对象"
    status = proposal.get("status")
    if status not in {"patch", "refusal"}:
        return "status 必须是 patch 或 refusal"
    if status == "patch" and not isinstance(proposal.get("operations"), list):
        return "operations 必须是最多 8 项的数组"
    return None


def _request_proposal_repair(
    provider: LLMProvider,
    *,
    instruction: str,
    target_scope: dict[str, Any],
    protected_scope: dict[str, Any],
    editable_ids: list[str],
    score_context: dict[str, Any],
    candidate: Any,
    error: str,
    max_output_tokens: int,
) -> ProviderResponse:
    """Request one bounded format repair while keeping all server-owned safety limits."""

    system_prompt = (
        "Repair one Sera score-edit proposal. Return only the supplied JSON schema. The operations field MUST be a "
        "JSON array. Do not add operations that were not requested, do not broaden target_scope, and use only event "
        "IDs from editable_event_ids. If the candidate cannot be repaired without guessing musical intent, return a "
        "refusal. Unused operation fields must use neutral values: semitones=0, pitch='', dynamic='', articulations=[]."
    )
    payload = {
        "instruction": instruction.strip(),
        "candidate": candidate,
        "server_error": error,
        "target_scope": target_scope,
        "protected_scope": protected_scope,
        "editable_event_ids": editable_ids,
        "score_context": score_context,
        "allowed_operations": list(ALLOWED_OPERATION_TYPES),
    }
    return provider.generate(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
        ],
        response_schema=llm_patch_proposal_schema(),
        temperature=0.0,
        max_tokens=max_output_tokens,
        metadata={"thinking": "disabled"},
    )


def _canonical_operations(raw: Any, editable_ids: list[str]) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) > 8:
        raise ValueError("operations 必须是最多 8 项的数组")
    allowed_ids = set(editable_ids)
    operations: list[dict[str, Any]] = []
    for raw_operation in raw:
        if not isinstance(raw_operation, dict):
            raise ValueError("operation 必须是对象")
        operation_type = str(raw_operation.get("type", ""))
        if operation_type not in ALLOWED_OPERATION_TYPES:
            raise ValueError(f"不支持的操作类型 {operation_type!r}")
        requested_ids = [str(value) for value in raw_operation.get("event_ids") or []]
        event_ids = list(editable_ids) if raw_operation.get("apply_to_all_selected") else list(dict.fromkeys(requested_ids))
        if not event_ids:
            raise ValueError("每项操作必须选择目标音符")
        unknown = [event_id for event_id in event_ids if event_id not in allowed_ids]
        if unknown:
            raise ValueError("提案包含宿主选区外或不存在的 event ID")
        arguments: dict[str, Any]
        expected_change_count: int | None = None
        if operation_type == "transpose":
            semitones = int(raw_operation.get("semitones", 0))
            if semitones == 0 or not -24 <= semitones <= 24:
                raise ValueError("transpose semitones 必须在 -24 到 24 之间且不能为 0")
            arguments = {"semitones": semitones}
            expected_change_count = len(event_ids)
        elif operation_type == "set_pitch":
            pitch = str(raw_operation.get("pitch", ""))
            if not PITCH_PATTERN.fullmatch(pitch):
                raise ValueError("set_pitch 必须使用如 C4、F#5 或 Bb3 的音高")
            arguments = {"pitch": pitch}
        elif operation_type == "set_dynamic":
            dynamic = str(raw_operation.get("dynamic", ""))
            if dynamic not in ALLOWED_DYNAMICS:
                raise ValueError("set_dynamic 使用了不支持的力度")
            arguments = {"dynamic": dynamic}
        else:
            articulations = list(dict.fromkeys(str(value) for value in raw_operation.get("articulations") or []))
            if not articulations or any(value not in ALLOWED_ARTICULATIONS for value in articulations):
                raise ValueError("set_articulation 仅支持 staccato、accent、tenuto")
            arguments = {"articulations": articulations}
        operations.append(
            {
                "operation_id": f"op_{len(operations) + 1:03d}",
                "type": operation_type,
                "selector": {"event_ids": event_ids},
                "arguments": arguments,
                "preconditions": [],
                "expected_change_count": expected_change_count,
            }
        )
    return operations


def _patch_id(
    score: dict[str, Any],
    fingerprint: str,
    instruction: str,
    operations: list[dict[str, Any]],
) -> str:
    encoded = json.dumps(
        {
            "score_id": score.get("score_id"),
            "fingerprint": fingerprint,
            "instruction": instruction,
            "operations": operations,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"llm_{hashlib.sha256(encoded).hexdigest()[:20]}"

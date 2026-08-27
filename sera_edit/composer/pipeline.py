"""End-to-end Sera Composer planning, realization, criticism, and ranking."""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from typing import Any

from backend.services.score_document_service import normalize_score_document
from sera_edit.composer.candidate_generator import generate_candidate_patches
from sera_edit.composer.critics import review_candidate
from sera_edit.composer.phrase_analysis import analyze_phrase
from sera_edit.composer.planner import plan_composition
from sera_edit.composer.preference import ComposerPreferenceStore
from sera_edit.composer.refinement import default_composer_refinement_store
from sera_edit.composer.run_trace import ComposerRunTraceStore
from sera_edit.composer.style_knowledge import retrieve_style_knowledge
from sera_edit.composer.texture_analysis import analyze_texture
from sera_edit.domain.score_scope import ScoreScope
from sera_edit.execution.transaction import PatchTransaction
from sera_edit.providers.base import LLMProvider
from sera_edit.providers.runtime import (
    DEFAULT_COMPOSER_LLM_TIMEOUT_SECONDS,
    LLMRuntimeSettings,
    composer_timeout_seconds,
    create_runtime_provider,
    runtime_settings,
)


BASELINE_GUARANTEES = {
    "canonical_score_document": True,
    "source_fingerprint_bound": True,
    "target_scope_bound": True,
    "protected_scope_enforced": True,
    "transaction_preview": True,
    "preserve_rhythm": True,
    "preserve_event_count": True,
    "preserve_instrumentation": True,
    "preserve_host_layout": True,
    "source_preserving_musicxml_compatible": True,
    "preference_feedback_local_only": True,
}

DEFAULT_COMPOSER_LLM_MAX_OUTPUT_TOKENS = 2048
RESPONSIVE_LOCAL_SEARCH_WIDTH = 8


def generate_composition_candidates(
    score_document: dict[str, Any],
    brief: str,
    target_scope: dict[str, Any],
    protected_scope: dict[str, Any] | None = None,
    *,
    candidate_count: int = 3,
    seed: int = 42,
    provider: LLMProvider | None = None,
    max_tokens: int = 1800,
    search_width: int = 16,
    preference_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate validated candidates without applying any score mutation."""

    score = normalize_score_document(score_document)
    plan, theory, planner_evidence = plan_composition(
        score,
        brief,
        target_scope,
        protected_scope,
        seed=seed,
        provider=provider,
        max_tokens=max_tokens,
    )
    style_knowledge = retrieve_style_knowledge(
        brief,
        plan.style_family,
        plan.mode,
        score_document=score,
        target_scope=plan.target_scope,
    )
    phrase_analysis = analyze_phrase(score, plan.target_scope)
    texture_analysis = analyze_texture(score, plan.target_scope)
    if plan.mode == "orchestration_advice":
        return {
            "status": "plan_only",
            "reason": "Composer V0.1 可生成可追溯的配器方案，但宿主桥当前不安全应用换乐器、增删声部等结构变化。",
            "apply_supported": False,
            "plan": plan.as_dict(),
            "theory_context": theory,
            "style_knowledge": _style_evidence(style_knowledge),
            "phrase_analysis": phrase_analysis,
            "texture_analysis": texture_analysis,
            "search_summary": {"search_width": 0, "evaluated": 0, "valid": 0, "returned": 0},
            "preference_profile": preference_profile or _empty_preference_profile(),
            "comparison_id": None,
            "failure_analysis": None,
            "planner": planner_evidence,
            "candidates": [],
            "selected_candidate_id": None,
            "baseline_guarantees": dict(BASELINE_GUARANTEES) | {"source_preserving_musicxml_compatible": False},
        }
    bounded_search_width = max(candidate_count, min(32, int(search_width)))
    patches = generate_candidate_patches(
        score,
        plan,
        candidate_count=bounded_search_width,
        phrase_analysis=phrase_analysis,
        style_knowledge=style_knowledge,
    )
    candidates: list[dict[str, Any]] = []
    for index, patch in enumerate(patches, start=1):
        preview = PatchTransaction().execute(score, patch, dry_run=True).as_dict()
        proposed = preview.get("proposed_score_document") or score
        review = review_candidate(
            score,
            proposed,
            plan,
            preview,
            style_knowledge=style_knowledge,
            phrase_analysis=phrase_analysis,
            preference_profile=preference_profile,
        )
        candidates.append(
            {
                "candidate_id": f"{plan.plan_id}_v{index}",
                "rank": 0,
                "label": f"候选 {index}",
                "patch": patch,
                "preview": preview,
                "review": review,
                "explanation": _candidate_explanation(plan, review),
            }
        )
    candidates.sort(
        key=lambda item: (
            item["review"]["status"] != "valid",
            -float(item["review"]["overall_score"]),
            item["candidate_id"],
        )
    )
    valid_pool = [candidate for candidate in candidates if candidate["review"]["status"] == "valid"]
    selected = _select_diverse_candidates(valid_pool, max(1, min(4, int(candidate_count))))
    rejected_pool = [candidate for candidate in candidates if candidate["review"]["status"] != "valid"]
    unreturned_valid = [candidate for candidate in valid_pool if candidate not in selected]
    selected.sort(key=lambda item: (-float(item["review"]["overall_score"]), item["candidate_id"]))
    for rank, candidate in enumerate(selected, start=1):
        candidate["rank"] = rank
        candidate["label"] = f"候选 {rank}"
    comparison_id = _comparison_id(plan.plan_id, selected)
    failure_analysis = None if selected else _analyze_candidate_failure(
        score,
        plan,
        phrase_analysis,
        candidates,
        generated_patch_count=len(patches),
        search_width=bounded_search_width,
    )
    return {
        "status": "generated" if selected else "unsupported",
        "reason": "" if selected else str(failure_analysis["summary"]),
        "apply_supported": bool(selected),
        "plan": plan.as_dict(),
        "theory_context": theory,
        "style_knowledge": _style_evidence(style_knowledge),
        "phrase_analysis": phrase_analysis,
        "texture_analysis": texture_analysis,
        "planner": planner_evidence,
        "candidates": selected,
        "selected_candidate_id": selected[0]["candidate_id"] if selected else None,
        "comparison_id": comparison_id if selected else None,
        "failure_analysis": failure_analysis,
        "search_summary": {
            "search_width": bounded_search_width,
            "evaluated": len(candidates),
            "valid": len(valid_pool),
            "rejected": len(rejected_pool),
            "valid_not_returned": len(unreturned_valid),
            "returned": len(selected),
            "selection": "overall_score_plus_pitch_diversity",
        },
        "preference_profile": preference_profile or _empty_preference_profile(),
        "baseline_guarantees": dict(BASELINE_GUARANTEES),
    }


def compose_with_runtime(
    score_document: dict[str, Any],
    brief: str,
    target_scope: dict[str, Any],
    protected_scope: dict[str, Any] | None = None,
    *,
    candidate_count: int = 3,
    seed: int = 42,
    settings: LLMRuntimeSettings | None = None,
    provider: LLMProvider | None = None,
    use_live_planner: bool = True,
    search_width: int = 16,
) -> dict[str, Any]:
    """Use the configured LLM for planning and deterministic local realization."""

    resolved = settings or runtime_settings()
    # The refinement runs in the background, so a slow reasoning model can use
    # its own longer budget without delaying the first local safe candidates.
    planner_timeout = composer_llm_timeout_seconds()
    planner_settings = replace(resolved, timeout_seconds=planner_timeout)
    live_provider = None
    if use_live_planner:
        live_provider = provider or create_runtime_provider(planner_settings)
    preference_profile = ComposerPreferenceStore().profile()
    try:
        result = generate_composition_candidates(
            score_document,
            brief,
            target_scope,
            protected_scope,
            candidate_count=candidate_count,
            seed=seed,
            provider=live_provider,
            max_tokens=min(resolved.max_output_tokens, composer_llm_max_output_tokens()),
            search_width=search_width,
            preference_profile=preference_profile,
        )
    except ValueError as exc:
        return {
            "status": "unsupported",
            "reason": str(exc),
            "apply_supported": False,
            "plan": None,
            "theory_context": [],
            "style_knowledge": None,
            "phrase_analysis": None,
            "texture_analysis": None,
            "search_summary": {"search_width": 0, "evaluated": 0, "valid": 0, "returned": 0},
            "preference_profile": preference_profile,
            "comparison_id": None,
            "failure_analysis": {
                "code": "invalid_target_or_instruction",
                "summary": str(exc),
                "suggestions": ["在 MuseScore 中重新框选包含音符的 1–8 个小节，然后再次发送给 Sera。"],
                "counts": {"evaluated": 0, "valid": 0, "rejected": 0},
                "failed_check_counts": {},
                "error_code_counts": {},
                "rejected_examples": [],
            },
            "planner": {"planner": "none", "fallback_reason": str(exc)},
            "candidates": [],
            "selected_candidate_id": None,
            "baseline_guarantees": dict(BASELINE_GUARANTEES),
        }
    if not use_live_planner:
        result["planner"]["planner"] = "deterministic_theory"
        result["planner"]["fallback_reason"] = "已按请求立即使用本地确定性理论计划。"
    result["planner"]["timeout_seconds"] = planner_timeout
    result["provider_status"] = resolved.public_status()
    try:
        result["run_trace"] = ComposerRunTraceStore().record(
            score_document=score_document,
            brief=brief,
            target_scope=target_scope,
            protected_scope=protected_scope or {},
            planner_mode="auto" if use_live_planner else "local",
            result=result,
        )
    except OSError as exc:
        result["run_trace"] = {"trace_id": None, "persisted": False, "error": str(exc)}
    return result


def compose_responsive_with_runtime(
    score_document: dict[str, Any],
    brief: str,
    target_scope: dict[str, Any],
    protected_scope: dict[str, Any] | None = None,
    *,
    candidate_count: int = 3,
    seed: int = 42,
    settings: LLMRuntimeSettings | None = None,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Return a local draft first while a live high-level plan runs in the background."""

    resolved = settings or runtime_settings()
    live_available = provider is not None or resolved.available
    if not live_available:
        return compose_with_runtime(
            score_document,
            brief,
            target_scope,
            protected_scope,
            candidate_count=candidate_count,
            seed=seed,
            settings=resolved,
            provider=None,
            use_live_planner=False,
            search_width=RESPONSIVE_LOCAL_SEARCH_WIDTH,
        )

    score_snapshot = deepcopy(score_document)
    target_snapshot = deepcopy(target_scope)
    protected_snapshot = deepcopy(protected_scope or {})
    store = default_composer_refinement_store()
    try:
        job = store.start(
            lambda: compose_with_runtime(
                score_snapshot,
                brief,
                target_snapshot,
                protected_snapshot,
                candidate_count=candidate_count,
                seed=seed,
                settings=resolved,
                provider=provider,
                use_live_planner=True,
                search_width=16,
            )
        )
    except RuntimeError as exc:
        local_result = compose_with_runtime(
            score_document,
            brief,
            target_scope,
            protected_scope,
            candidate_count=candidate_count,
            seed=seed,
            settings=resolved,
            provider=None,
            use_live_planner=False,
            search_width=RESPONSIVE_LOCAL_SEARCH_WIDTH,
        )
        local_result["planner"]["fallback_reason"] = str(exc)
        local_result["refinement"] = {
            "job_id": "",
            "status": "failed",
            "created_at": None,
            "completed_at": None,
            "error": str(exc),
        }
        return local_result
    local_result = compose_with_runtime(
        score_document,
        brief,
        target_scope,
        protected_scope,
        candidate_count=candidate_count,
        seed=seed,
        settings=resolved,
        provider=None,
        use_live_planner=False,
        search_width=RESPONSIVE_LOCAL_SEARCH_WIDTH,
    )
    current = store.get(str(job["job_id"]))
    if current["status"] == "ready" and isinstance(current.get("result"), dict):
        refined = dict(current["result"])
        refined["refinement"] = _refinement_evidence(current, include_result=False)
        return refined
    local_result["planner"]["fallback_reason"] = (
        "本地安全初稿已先返回；实时 LLM 正在后台优化，不再阻塞候选生成。"
        if current["status"] == "running"
        else f"本地安全初稿已返回；后台 LLM 优化失败：{current.get('error') or '未知错误'}"
    )
    local_result["refinement"] = _refinement_evidence(current, include_result=False)
    return local_result


def composer_llm_timeout_seconds() -> float:
    """Compatibility wrapper for the non-blocking Composer refinement budget."""

    return composer_timeout_seconds()


def composer_llm_max_output_tokens() -> int:
    """Keep the high-level CompositionPlan response short and inexpensive."""

    raw = os.getenv("SERA_COMPOSER_LLM_MAX_OUTPUT_TOKENS", str(DEFAULT_COMPOSER_LLM_MAX_OUTPUT_TOKENS))
    try:
        value = int(raw)
    except ValueError:
        value = DEFAULT_COMPOSER_LLM_MAX_OUTPUT_TOKENS
    return max(512, min(value, 8192))


def _refinement_evidence(snapshot: dict[str, Any], *, include_result: bool) -> dict[str, Any]:
    allowed = {"job_id", "status", "created_at", "completed_at", "error"}
    if include_result:
        allowed.add("result")
    return {key: deepcopy(value) for key, value in snapshot.items() if key in allowed}


def _candidate_explanation(plan: Any, review: dict[str, Any]) -> str:
    progression = " – ".join(plan.harmonic_progression)
    return (
        f"{plan.style_family} / {plan.texture}；和声 {progression}。"
        f"修改 {review['changed_event_count']} 个音高；动机 {round(review['motif_score'] * 100)}，"
        f"乐句 {round(review['phrase_score'] * 100)}，风格 {round(review['style_score'] * 100)}。"
        f"和弦骨干命中率 {round(review['chord_tone_ratio'] * 100)}%，"
        f"保留原节奏、事件数量、配器与宿主排版。"
    )


def _style_evidence(style_knowledge: dict[str, Any]) -> dict[str, Any]:
    profile = style_knowledge["profile"]
    return {
        "knowledge_base_id": style_knowledge["knowledge_base_id"],
        "schema_version": style_knowledge["schema_version"],
        "fingerprint": style_knowledge["fingerprint"],
        "style_id": style_knowledge["style_id"],
        "display_name_zh": style_knowledge["display_name_zh"],
        "matched_rules": style_knowledge["matched_rules"],
        "query": style_knowledge["query"],
        "query_fingerprint": style_knowledge["query_fingerprint"],
        "retrieval": style_knowledge["retrieval"],
        "profile_schema_version": style_knowledge["profile_schema_version"],
        "planning": profile["planning"],
        "melody": profile["melody"],
        "voice_leading": profile["voice_leading"],
        "critic_weights": profile["critic_weights"],
        "provenance": style_knowledge["provenance"],
    }


def _select_diverse_candidates(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if not candidates or limit <= 0:
        return []
    remaining = list(candidates)
    selected = [remaining.pop(0)]
    while remaining and len(selected) < limit:
        choice = max(
            remaining,
            key=lambda candidate: (
                float(candidate["review"]["overall_score"])
                + 0.12 * min(_pitch_diversity(candidate, picked) for picked in selected),
                float(candidate["review"]["overall_score"]),
                candidate["candidate_id"],
            ),
        )
        selected.append(choice)
        remaining.remove(choice)
    return selected


def _pitch_diversity(left: dict[str, Any], right: dict[str, Any]) -> float:
    def values(candidate: dict[str, Any]) -> dict[str, str]:
        return {
            str(operation.get("selector", {}).get("event_ids", [""])[0]): str(operation.get("arguments", {}).get("pitch", ""))
            for operation in candidate.get("patch", {}).get("operations", [])
            if operation.get("type") == "set_pitch" and operation.get("selector", {}).get("event_ids")
        }

    first, second = values(left), values(right)
    event_ids = set(first) | set(second)
    if not event_ids:
        return 0.0
    return sum(first.get(event_id) != second.get(event_id) for event_id in event_ids) / len(event_ids)


def _comparison_id(plan_id: str, candidates: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        {"plan_id": plan_id, "candidate_ids": [item["candidate_id"] for item in candidates]},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "comparison_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def _empty_preference_profile() -> dict[str, Any]:
    return {
        "schema_version": "0.2.0",
        "feedback_count": 0,
        "dimension_targets": {},
        "reason_counts": {"motif": 0, "phrase": 0, "style": 0, "harmony": 0, "playability": 0},
        "preferred_styles": {},
        "active": False,
        "privacy": {"local_only": True, "stores_score_content": False, "stores_user_identity": False},
    }


def _analyze_candidate_failure(
    score: dict[str, Any],
    plan: Any,
    phrase_analysis: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    generated_patch_count: int,
    search_width: int,
) -> dict[str, Any]:
    """Explain a fail-closed candidate set without exposing an unsafe patch."""

    target_scope = ScoreScope.from_dict(plan.target_scope)
    protected_scope = ScoreScope.from_dict(plan.protected_scope)
    target_notes = [context for context in target_scope.select(score) if context.event.get("type") == "note"]
    protected_notes = [context for context in target_notes if protected_scope.contains(context)]
    editable_notes = [context for context in target_notes if not protected_scope.contains(context)]
    primary_voice_id = str(phrase_analysis.get("primary_voice_id") or "")
    realizable_notes = [
        context
        for context in editable_notes
        if not (
            plan.mode == "reharmonize"
            and plan.preserve_melody
            and f"{context.staff}:v{context.voice}" == primary_voice_id
        )
    ]

    failed_checks: Counter[str] = Counter()
    error_codes: Counter[str] = Counter()
    rejected_examples: list[dict[str, Any]] = []
    for candidate in candidates:
        report = candidate.get("preview", {}).get("validation_report", {})
        review = candidate.get("review", {})
        transaction_status = str(report.get("status") or "invalid")
        errors = report.get("errors") or []
        codes = [str(error.get("code") or "unknown") for error in errors]
        error_codes.update(codes)
        if transaction_status not in {"valid", "warning"}:
            failed_checks["transaction_validation"] += 1
        if "E11" in codes:
            failed_checks["protected_scope"] += 1
        scaffold = next(
            (finding for finding in review.get("findings") or [] if finding.get("check") == "host_scaffold_preserved"),
            None,
        )
        if scaffold is not None and not scaffold.get("passed"):
            failed_checks["rhythm_or_structure"] += 1
        introduced_playability = int(review.get("introduced_range_violation_count") or 0) + int(
            review.get("introduced_voice_crossing_count") or 0
        )
        if introduced_playability:
            failed_checks["new_playability_conflict"] += 1
        if review.get("status") == "rejected" and len(rejected_examples) < 3:
            rejected_examples.append(
                {
                    "candidate_id": str(candidate.get("candidate_id") or ""),
                    "transaction_status": transaction_status,
                    "rollback_reason": candidate.get("preview", {}).get("rollback_reason"),
                    "error_codes": codes,
                    "failed_checks": [
                        name
                        for name, failed in (
                            ("transaction_validation", transaction_status not in {"valid", "warning"}),
                            ("protected_scope", "E11" in codes),
                            ("rhythm_or_structure", scaffold is not None and not scaffold.get("passed")),
                            ("new_playability_conflict", introduced_playability > 0),
                        )
                        if failed
                    ],
                    "scaffold_details": {
                        "event_count_preserved": review.get("event_count_preserved"),
                        "duration_preserved": review.get("duration_preserved"),
                        "pitch_only": review.get("pitch_only"),
                        "transaction_valid": review.get("transaction_valid"),
                        "changed_field_counts": review.get("changed_field_counts"),
                    },
                }
            )

    if not target_notes:
        code = "no_notes_in_target"
        summary = "当前宿主选区没有可编辑音符；Sera 未修改乐谱。"
        suggestions = ["在 MuseScore 中框选实际包含音符的小节，再点击“发送乐谱/选区到 Sera”。"]
    elif len(protected_notes) == len(target_notes):
        code = "target_fully_protected"
        summary = f"目标选区中的 {len(target_notes)} 个音符全部位于保护范围内；Sera 未越过保护边界。"
        suggestions = [
            "缩小保护范围，或在 MuseScore 中只选择允许改写的谱表/声部。",
            "如果要保留旋律，请把伴奏声部纳入目标选区，而不是同时保护全部目标音符。",
        ]
    elif plan.mode == "reharmonize" and plan.preserve_melody and not realizable_notes:
        code = "no_accompaniment_to_reharmonize"
        summary = "当前选区只有需要保留的旋律线，没有可重新和声化的伴奏音符；Sera 未擅自改写旋律。"
        suggestions = [
            "选择同时包含旋律与伴奏的范围，或只选择左手/伴奏声部。",
            "若想改旋律，请将目标改写为“旋律变奏”而不是“保留旋律的重新和声化”。",
        ]
    elif not candidates:
        code = "no_distinct_pitch_candidates"
        summary = "选区内没有产生与原谱不同、且仍满足当前约束的音高候选；乐谱保持不变。"
        suggestions = ["把创作目标写得更具体（风格、方向、终止或和声），或适当扩大选区。"]
    elif failed_checks["protected_scope"] == len(candidates):
        code = "protected_scope_conflict"
        summary = f"已评审 {len(candidates)} 个候选，但它们都触及保护范围；Sera 已全部回滚。"
        suggestions = ["检查目标范围与保护范围是否重叠，并重新发送宿主选区。"]
    elif failed_checks["new_playability_conflict"] == len(candidates):
        code = "new_playability_conflicts"
        summary = f"已评审 {len(candidates)} 个候选，但每个候选都会新增音域越界或声部交叉；Sera 已全部拒绝。"
        suggestions = [
            "缩小到单一旋律声部，或在指令中明确乐器与期望音域。",
            "也可以选择更短的 1–2 小节，让 Composer 重新搜索。",
        ]
    elif failed_checks["transaction_validation"] == len(candidates):
        code = "transaction_validation_failed"
        summary = f"已评审 {len(candidates)} 个候选，但全部未通过乐谱事务验证；原谱没有被修改。"
        suggestions = [
            "在 MuseScore 中保存当前乐谱并重新发送，避免 Sera 使用过期的乐谱指纹。",
            "展开下方诊断，按错误代码检查拍号、时值或记谱关系。",
        ]
    else:
        code = "all_candidates_rejected"
        summary = f"已评审 {len(candidates)} 个候选，但没有候选同时满足全部硬约束；原谱没有被修改。"
        suggestions = ["缩小选区或减少相互冲突的要求后重试；Sera 不会绕过事务与保护范围。"]

    return {
        "code": code,
        "summary": summary,
        "suggestions": suggestions,
        "counts": {
            "target_notes": len(target_notes),
            "protected_target_notes": len(protected_notes),
            "editable_target_notes": len(editable_notes),
            "realizable_target_notes": len(realizable_notes),
            "search_width": search_width,
            "generated_patches": generated_patch_count,
            "evaluated": len(candidates),
            "valid": sum(candidate.get("review", {}).get("status") == "valid" for candidate in candidates),
            "rejected": sum(candidate.get("review", {}).get("status") != "valid" for candidate in candidates),
        },
        "failed_check_counts": dict(sorted(failed_checks.items())),
        "error_code_counts": dict(sorted(error_codes.items())),
        "rejected_examples": rejected_examples,
    }

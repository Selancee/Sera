"""Independent strict patch routes that do not replace legacy Workbench APIs."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sera_edit.composer.pipeline import compose_responsive_with_runtime, compose_with_runtime
from sera_edit.composer.preference import ComposerPreferenceStore
from sera_edit.composer.refinement import default_composer_refinement_store
from sera_edit.composer.run_trace import ComposerRunTraceStore
from sera_edit.composer.knowledge_repository import default_composer_knowledge_repository
from sera_edit.composer.style_knowledge import default_style_knowledge_base
from sera_edit.execution.transaction import PatchTransaction
from sera_edit.generation.conversation_agent import converse_with_runtime
from sera_edit.generation.llm_patch_generator import generate_patch_with_runtime
from sera_edit.providers.runtime import (
    clear_runtime_configuration,
    runtime_settings,
    save_runtime_configuration,
)
from sera_edit.review.benchmark_review import ISSUE_CODES, default_benchmark_review_service
from sera_edit.validation.schema_validator import validate_patch_schema


router = APIRouter(prefix="/sera-edit", tags=["SeraEdit Research"])


class StrictPatchRequest(BaseModel):
    """Canonical score and strict ScorePatch request payload."""

    score_document: dict[str, Any]
    patch: dict[str, Any]


class StrictGeneratePreviewRequest(BaseModel):
    """Bounded local instruction generation plus strict transaction preview."""

    score_document: dict[str, Any]
    instruction: str = Field(min_length=1)
    target_scope: dict[str, Any]
    protected_scope: dict[str, Any] = Field(default_factory=dict)


class ConversationTurn(BaseModel):
    """One bounded user/assistant turn supplied as conversational context."""

    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=8000)


class ConversationRequest(BaseModel):
    """Plain conversation request; this route cannot generate or apply a patch."""

    message: str = Field(min_length=1, max_length=8000)
    history: list[ConversationTurn] = Field(default_factory=list, max_length=12)
    score_document: dict[str, Any] | None = None
    target_scope: dict[str, Any] = Field(default_factory=dict)


class CompositionPreviewRequest(BaseModel):
    """A bounded creative brief over an existing host-score scaffold."""

    score_document: dict[str, Any]
    brief: str = Field(min_length=1, max_length=8000)
    target_scope: dict[str, Any]
    protected_scope: dict[str, Any] = Field(default_factory=dict)
    candidate_count: int = Field(default=3, ge=1, le=4)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    planner_mode: Literal["auto", "local"] = "auto"


class CompositionPreferenceRequest(BaseModel):
    """One explicit local A/B preference without score or identity data."""

    comparison_id: str = Field(min_length=1, max_length=120)
    plan_id: str = Field(min_length=1, max_length=120)
    style_family: str = Field(min_length=1, max_length=40)
    selected_candidate_id: str = Field(min_length=1, max_length=160)
    rejected_candidate_ids: list[str] = Field(default_factory=list, max_length=8)
    selected_review: dict[str, float] = Field(default_factory=dict)
    reasons: list[Literal["motif", "phrase", "style", "harmony", "playability"]] = Field(
        default_factory=list,
        max_length=5,
    )


class ProviderConfigurationRequest(BaseModel):
    """Secret-bearing local request; the API key is never echoed in responses."""

    provider: str = Field(min_length=1, max_length=40)
    model: str = Field(default="", max_length=200)
    api_key: str | None = Field(default=None, max_length=4096)
    base_url: str = Field(default="", max_length=500)
    fallback_local: bool = True
    reasoning_effort: str = Field(default="low", max_length=20)
    composer_timeout_seconds: float = Field(default=180.0, ge=30.0, le=600.0)


class BenchmarkReviewRequest(BaseModel):
    """One traceable human decision for a benchmark task."""

    task_id: str = Field(min_length=1, max_length=120)
    reviewer_id: str = Field(min_length=1, max_length=80)
    reviewer_role: Literal["primary", "secondary"] = "primary"
    decision: Literal["compliant", "needs_revision", "exclude"]
    dimensions: dict[str, int]
    issue_codes: list[str] = Field(default_factory=list, max_length=len(ISSUE_CODES))
    notes: str = Field(default="", max_length=4000)


@router.post("/schema-validate")
def schema_validate(request: StrictPatchRequest) -> dict[str, Any]:
    """Validate only the strict ScorePatch JSON contract."""

    return validate_patch_schema(request.patch).as_dict()


@router.post("/generate-preview")
def generate_preview(request: StrictGeneratePreviewRequest) -> dict[str, Any]:
    """Generate a bounded live/local patch and run the complete dry transaction."""

    payload = generate_patch_with_runtime(
        request.score_document,
        request.instruction,
        request.target_scope,
        request.protected_scope,
    )
    payload["preview"] = (
        PatchTransaction().execute(request.score_document, payload["patch"], dry_run=True).as_dict()
        if payload.get("patch") is not None
        else None
    )
    return payload


@router.post("/chat")
def chat(request: ConversationRequest) -> dict[str, Any]:
    """Return a plain-language answer through a path with no patch transaction."""

    return converse_with_runtime(
        request.message,
        [turn.model_dump() for turn in request.history],
        request.score_document,
        request.target_scope,
    )


@router.post("/composer/preview")
def composer_preview(request: CompositionPreviewRequest) -> dict[str, Any]:
    """Plan and rank creative candidates without mutating the host score."""

    compose = compose_responsive_with_runtime if request.planner_mode == "auto" else compose_with_runtime
    return compose(
        request.score_document,
        request.brief,
        request.target_scope,
        request.protected_scope,
        candidate_count=request.candidate_count,
        seed=request.seed,
        **({"use_live_planner": False} if request.planner_mode == "local" else {}),
    )


@router.get("/composer/refinements/{job_id}")
def composer_refinement(job_id: str) -> dict[str, Any]:
    """Poll a background live-LLM refinement without exposing credentials."""

    try:
        return default_composer_refinement_store().get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Composer 后台优化任务不存在或已过期。") from exc


@router.post("/composer/feedback")
def composer_feedback(request: CompositionPreferenceRequest) -> dict[str, Any]:
    """Persist an explicit local preference and return the updated profile."""

    rejected = [candidate_id for candidate_id in request.rejected_candidate_ids if candidate_id != request.selected_candidate_id]
    try:
        return ComposerPreferenceStore().record(
            comparison_id=request.comparison_id,
            plan_id=request.plan_id,
            style_family=request.style_family,
            selected_candidate_id=request.selected_candidate_id,
            rejected_candidate_ids=rejected,
            selected_review=request.selected_review,
            reasons=list(request.reasons),
        )
    except OSError as exc:
        raise HTTPException(status_code=500, detail="无法写入本机 Composer 偏好文件。") from exc


@router.get("/composer/preference-profile")
def composer_preference_profile() -> dict[str, Any]:
    """Return the local aggregate preference profile without raw score data."""

    return ComposerPreferenceStore().profile()


@router.get("/composer/style-knowledge")
def composer_style_knowledge() -> dict[str, Any]:
    """Describe the installed versioned style knowledge base."""

    repository = default_composer_knowledge_repository()
    profiles = default_style_knowledge_base()
    return repository.status() | {
        "style_ids": list(profiles.style_ids),
        "profile_schema_version": profiles.schema_version,
        "profile_fingerprint": profiles.fingerprint,
    }


@router.get("/composer/latest-run")
def composer_latest_run() -> dict[str, Any]:
    """Return the latest privacy-bounded local planning trace."""

    trace = ComposerRunTraceStore().latest()
    return {"available": trace is not None, "trace": trace}


@router.get("/review/summary")
def benchmark_review_summary() -> dict[str, Any]:
    """Return human-review progress and evidence-based calibration gates."""

    try:
        return default_benchmark_review_service().summary()
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/review/tasks")
def benchmark_review_tasks(
    category: str = "",
    status: str = "",
    runtime_status: str = "",
    search: str = "",
) -> dict[str, Any]:
    """List benchmark tasks without sending full score documents to the UI."""

    try:
        return default_benchmark_review_service().list_tasks(
            category=category,
            status=status,
            runtime_status=runtime_status,
            search=search,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/review/tasks/{task_id}")
def benchmark_review_task(task_id: str) -> dict[str, Any]:
    """Return one task's scope, gold operations, deterministic diff, and reviews."""

    try:
        return default_benchmark_review_service().task_detail(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown benchmark task: {task_id}") from exc
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/review/decisions")
def save_benchmark_review(request: BenchmarkReviewRequest) -> dict[str, Any]:
    """Append one review; benchmark source files remain immutable."""

    try:
        return default_benchmark_review_service().submit_review(request.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown benchmark task: {request.task_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not write the local benchmark review store.") from exc


@router.post("/review/tasks/{task_id}/artifacts/{variant}")
def prepare_benchmark_review_artifact(task_id: str, variant: str) -> dict[str, Any]:
    """Prepare Gold or product-runtime MusicXML for inspection in the host."""

    try:
        return default_benchmark_review_service().prepare_artifact(task_id, variant)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown benchmark task: {task_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/review/export")
def export_benchmark_reviews() -> dict[str, Any]:
    """Write JSON and CSV snapshots without modifying benchmark task assets."""

    try:
        return default_benchmark_review_service().export_reviews()
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/provider-status")
def provider_status() -> dict[str, object]:
    """Report live-LLM readiness without returning any credential value."""

    return runtime_settings().public_status()


@router.put("/provider-configuration")
def update_provider_configuration(request: ProviderConfigurationRequest) -> dict[str, object]:
    """Encrypt, persist, and activate an in-app provider configuration."""

    try:
        settings = save_runtime_configuration(
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
            base_url=request.base_url,
            fallback_local=request.fallback_local,
            reasoning_effort=request.reasoning_effort,
            composer_timeout_seconds_value=request.composer_timeout_seconds,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"saved": True, "status": settings.public_status()}


@router.delete("/provider-configuration")
def delete_provider_configuration() -> dict[str, object]:
    """Remove the stored credential and return to deterministic local rules."""

    try:
        settings = clear_runtime_configuration()
    except OSError as exc:
        raise HTTPException(status_code=500, detail="无法更新本机模型配置。") from exc
    return {"saved": True, "status": settings.public_status()}


@router.post("/preview")
def preview_patch(request: StrictPatchRequest) -> dict[str, Any]:
    """Run the complete transaction without committing caller state."""

    return PatchTransaction().execute(request.score_document, request.patch, dry_run=True).as_dict()


@router.post("/apply")
def apply_patch(request: StrictPatchRequest) -> dict[str, Any]:
    """Apply only after all validation layers and MusicXML round-trip pass."""

    return PatchTransaction().execute(request.score_document, request.patch).as_dict()

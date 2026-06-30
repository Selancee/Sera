"""FastAPI app for the Sera MVP."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency-light test/runtime fallback.
    def load_dotenv(*_: object, **__: object) -> bool:
        return False

from backend.agents.score_editing_agent import ScoreEditingAgent
from backend.llm.provider_factory import create_llm_provider
from backend.pipeline import SeraPipeline
from backend.services.prompt_alignment_service import score_prompt_alignment
from backend.services.accompaniment_service import generate_left_hand_accompaniment_patch
from backend.services.project_migration_service import migrate_workbench_project, project_summary
from backend.services.score_document_service import (
    load_score_project,
    musicxml_to_score_document,
    save_score_project,
    score_document_to_musicxml,
    score_document_to_note_events,
)
from backend.services.score_operation_service import apply_operations, apply_score_operation, record_operation, redo_last, replay_operations, undo_last
from backend.services.score_patch_service import ScorePatchService


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# TODO: move environment validation into a dedicated settings module when Sera
# grows more runtime configuration knobs.
load_dotenv(PROJECT_ROOT / ".env")
pipeline = SeraPipeline(PROJECT_ROOT)
score_editing_agent = ScoreEditingAgent()
score_patch_service = ScorePatchService()

app = FastAPI(
    title="Sera API",
    version="0.2.0",
    description="Agent-assisted symbolic music generation API.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    """Request body for /generate."""

    prompt: str = Field(min_length=1, max_length=2000)
    generator_mode: Literal["rule_based", "model_based", "model", "hybrid_v04", "hybrid_v05", "hybrid_v05_no_postprocess"] | None = None
    model_task_type: Literal["melody_fragment", "motif_variation", "cadence_generation", "rhythm_rewrite"] | None = None


class ReviseRequest(BaseModel):
    """Request body for /revise."""

    run_id: str
    feedback: str = Field(default="", max_length=2000)


class ExportRequest(BaseModel):
    """Request body for /export."""

    run_id: str
    format: Literal["musicxml", "midi", "abc", "pdf", "plan", "json_plan", "validation_report", "experiment_log"]


class EvaluateRequest(BaseModel):
    """Request body for /evaluate."""

    run_id: str


class ModelSampleRequest(BaseModel):
    """Request body for /model/sample."""

    prompt: str = Field(min_length=1, max_length=2000)
    max_tokens: int = Field(default=96, ge=8, le=256)


class ModelSelectRequest(BaseModel):
    """Request body for /model/select."""

    model_name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    persist: bool = True


class RatingRequest(BaseModel):
    """Request body for /rate."""

    run_id: str
    prompt_adherence: int = Field(default=3, ge=1, le=5)
    musical_coherence: int = Field(default=3, ge=1, le=5)
    notation_readability: int = Field(default=3, ge=1, le=5)
    playability: int = Field(default=3, ge=1, le=5)
    editability: int = Field(default=3, ge=1, le=5)
    preference: str = Field(default="no_preference", max_length=80)
    notes: str = Field(default="", max_length=2000)
    rater_id: str = Field(default="local_demo", max_length=80)


class ImportMusicXMLRequest(BaseModel):
    """Request body for /score/import_musicxml."""

    musicxml: str = Field(min_length=1)
    prompt: str = Field(default="", max_length=2000)


class ScoreDocumentRequest(BaseModel):
    """Request body carrying a V0.6 ScoreDocument."""

    score_document: dict[str, Any]


class ApplyOperationRequest(BaseModel):
    """Request body for /score/apply_operation."""

    score_document: dict[str, Any]
    operation: dict[str, Any]
    operation_history: dict[str, Any] = Field(default_factory=lambda: {"done": [], "undone": []})


class BatchOperationsRequest(BaseModel):
    """Request body for /score/batch_operations."""

    score_document: dict[str, Any]
    operations: list[dict[str, Any]]
    operation_history: dict[str, Any] = Field(default_factory=lambda: {"done": [], "undone": []})


class LightValidateRequest(BaseModel):
    """Request body for /score/light_validate."""

    score_document: dict[str, Any]
    dirty_measures: list[int] = Field(default_factory=list)


class HistoryRequest(BaseModel):
    """Request body for undo/redo."""

    score_document: dict[str, Any]
    operation_history: dict[str, Any] = Field(default_factory=lambda: {"done": [], "undone": []})


class AgentEditRequest(BaseModel):
    """Request body for /score/agent_edit."""

    instruction: str = Field(min_length=1, max_length=2000)
    score_document: dict[str, Any]
    selected_range: dict[str, Any] = Field(default_factory=lambda: {"start_measure": 1, "end_measure": 1})
    constraints: dict[str, Any] = Field(default_factory=dict)
    current_score_summary: dict[str, Any] = Field(default_factory=dict)
    current_score_excerpt: dict[str, Any] = Field(default_factory=dict)
    agent_plan: dict[str, Any] = Field(default_factory=dict)
    current_selection: dict[str, Any] = Field(default_factory=dict)
    recent_operations: list[dict[str, Any]] = Field(default_factory=list)
    dirty_measures: list[int] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    playback_position: dict[str, Any] = Field(default_factory=dict)
    selected_notes_summary: dict[str, Any] = Field(default_factory=dict)
    user_edit_intent_inferred: str = Field(default="", max_length=500)
    preserve_user_edits_since_timestamp: str = Field(default="", max_length=100)


class PatchRequest(BaseModel):
    """Request body for patch preview/apply/reject."""

    score_document: dict[str, Any]
    patch: dict[str, Any]
    instruction: str = Field(default="", max_length=2000)
    selected_range: dict[str, Any] = Field(default_factory=lambda: {"start_measure": 1, "end_measure": 1})
    constraints: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="", max_length=500)


class PartialPatchRequest(PatchRequest):
    """Request body for /score/partial_apply_patch."""

    operation_ids: list[str] = Field(default_factory=list)
    operation_indexes: list[int] = Field(default_factory=list)
    apply_filter: Literal["selected", "all", "notes", "dynamics", "harmony", "measures"] = "selected"


class ExplainSelectionRequest(BaseModel):
    """Request body for /score/explain_selection."""

    score_document: dict[str, Any]
    selected_range: dict[str, Any] = Field(default_factory=lambda: {"start_measure": 1, "end_measure": 1})
    question: str = Field(default="", max_length=1000)


class SaveProjectRequest(BaseModel):
    """Request body for /score/save_project."""

    project_id: str = Field(default="", max_length=120)
    project: dict[str, Any]


class ProjectMigrationRequest(BaseModel):
    """Request body for /score/migrate_project and package export."""

    project: dict[str, Any]


class AccompanimentRequest(BaseModel):
    """Request body for /score/generate_accompaniment."""

    score_document: dict[str, Any]
    selected_range: dict[str, Any] = Field(default_factory=lambda: {"start_measure": 1, "end_measure": 1})
    texture: Literal["block_chord", "arpeggiated", "bass_chord"] = "arpeggiated"


class RevertAgentPatchRequest(BaseModel):
    """Request body for /score/revert_last_agent_patch."""

    score_document: dict[str, Any]
    operation_history: dict[str, Any] = Field(default_factory=lambda: {"done": [], "undone": []})
    patch_history: list[dict[str, Any]] = Field(default_factory=list)


class ContinueFromLastEditRequest(BaseModel):
    """Request body for /score/continue_from_last_edit."""

    score_document: dict[str, Any]
    selected_range: dict[str, Any] = Field(default_factory=lambda: {"start_measure": 1, "end_measure": 1})
    recent_operations: list[dict[str, Any]] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    instruction: str = Field(default="Continue from my last edit while preserving manual changes.", max_length=2000)


class LoadProjectRequest(BaseModel):
    """Request body for /score/load_project."""

    project_id: str = Field(min_length=1, max_length=120)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a small health response."""

    return {"status": "ok", "app": "Sera", "version": "0.2.0"}


@app.post("/generate")
def generate(request: GenerateRequest) -> dict[str, object]:
    """Generate a score from a natural-language prompt."""

    return pipeline.generate(request.prompt, generator_mode=request.generator_mode)


@app.post("/revise")
def revise(request: ReviseRequest) -> dict[str, object]:
    """Revise a previously generated score using feedback."""

    try:
        return pipeline.revise(request.run_id, request.feedback)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/export")
def export(request: ExportRequest) -> dict[str, str]:
    """Return an artifact URL for a run and format."""

    path = pipeline.artifact_path(request.run_id, request.format)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {
        "run_id": request.run_id,
        "format": request.format,
        "artifact_url": f"/export/{request.run_id}/{request.format}",
        "path": str(path),
    }


@app.get("/export/{run_id}/{file_format}")
def export_file(run_id: str, file_format: str) -> FileResponse:
    """Download an exported MusicXML, MIDI, ABC, or PDF artifact."""

    try:
        path = pipeline.artifact_path(run_id, file_format)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    media_types = {
        "musicxml": "application/vnd.recordare.musicxml+xml",
        "midi": "audio/midi",
        "abc": "text/plain",
        "pdf": "application/pdf",
        "plan": "application/json",
        "json_plan": "application/json",
        "validation_report": "application/json",
        "experiment_log": "application/json",
    }
    return FileResponse(path, media_type=media_types.get(file_format, "application/octet-stream"), filename=path.name)


@app.post("/evaluate")
def evaluate(request: EvaluateRequest) -> dict[str, object]:
    """Return evaluation metrics for a generated run."""

    try:
        return pipeline.evaluate_run(request.run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/model/status")
def model_status() -> dict[str, object]:
    """Return trained symbolic model status and latest run metrics."""

    return pipeline.symbolic_model_status()


@app.get("/model/registry")
def model_registry() -> dict[str, object]:
    """Return local symbolic models available for runtime selection."""

    return pipeline.symbolic_model_registry()


@app.post("/model/select")
def model_select(request: ModelSelectRequest) -> dict[str, object]:
    """Switch the main score generator to a local symbolic model."""

    try:
        return pipeline.select_symbolic_model(request.model_name, persist=request.persist)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/model/sample")
def model_sample(request: ModelSampleRequest) -> dict[str, object]:
    """Return a token-level qualitative sample from the symbolic model lab."""

    return pipeline.symbolic_model_sample(request.prompt, request.max_tokens)


@app.post("/rate")
def rate(request: RatingRequest) -> dict[str, object]:
    """Persist a human evaluation rating for a generated run."""

    try:
        return pipeline.rate_run(request.run_id, request.model_dump(exclude={"run_id"}))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/score/import_musicxml")
def score_import_musicxml(request: ImportMusicXMLRequest) -> dict[str, object]:
    """Import MusicXML into a canonical ScoreDocument."""

    try:
        score_document = musicxml_to_score_document(request.musicxml, prompt=request.prompt, source="imported")
        _append_score_event("import_musicxml", {"score_id": score_document.get("score_id", "")})
        return {"score_document": score_document, "operation_history": {"done": [], "undone": []}}
    except Exception as exc:  # noqa: BLE001 - route must return readable errors.
        raise HTTPException(status_code=400, detail=f"Could not import MusicXML: {exc}") from exc


@app.post("/score/export_musicxml")
def score_export_musicxml(request: ScoreDocumentRequest) -> dict[str, object]:
    """Export a ScoreDocument to MusicXML after validation."""

    try:
        musicxml = score_document_to_musicxml(request.score_document)
        validation = pipeline.musicxml_validator.validate_text(musicxml).to_report()
        if not validation.get("valid_musicxml"):
            raise ValueError(f"Export validation failed: {validation.get('errors', [])}")
        _append_score_event("export_musicxml", {"score_id": request.score_document.get("score_id", "")})
        return {"musicxml": musicxml, "validation_report": validation}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/score/export_midi")
def score_export_midi(request: ScoreDocumentRequest) -> dict[str, object]:
    """Export a ScoreDocument to a MIDI file."""

    try:
        export_dir = PROJECT_ROOT / "data" / "workbench_exports"
        export_id = uuid.uuid4().hex[:12]
        midi_path = export_dir / f"{export_id}.mid"
        note_events = score_document_to_note_events(request.score_document)
        tempo = int(request.score_document.get("global", {}).get("tempo", 90))
        pipeline.midi_exporter.write_midi(note_events, tempo, midi_path)
        _append_score_event("export_midi", {"path": str(midi_path)})
        return {"midi_path": str(midi_path), "note_event_count": len(note_events)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/score/export_pdf")
def score_export_pdf(request: ScoreDocumentRequest) -> dict[str, object]:
    """Export a ScoreDocument to PDF, falling back to stub PDF when needed."""

    try:
        export_dir = PROJECT_ROOT / "data" / "workbench_exports"
        export_id = uuid.uuid4().hex[:12]
        musicxml_path = export_dir / f"{export_id}.musicxml"
        pdf_path = export_dir / f"{export_id}.pdf"
        musicxml = score_document_to_musicxml(request.score_document)
        pipeline.musicxml_exporter.write_musicxml(musicxml, musicxml_path)
        pipeline.pdf_exporter.write_pdf(musicxml_path, pdf_path, str(request.score_document.get("title", "Sera Workbench")))
        _append_score_event("export_pdf", {"path": str(pdf_path)})
        return {"pdf_path": str(pdf_path), "musicxml_path": str(musicxml_path)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/score/validate")
def score_validate(request: ScoreDocumentRequest) -> dict[str, object]:
    """Validate a ScoreDocument through MusicXML export."""

    try:
        musicxml = score_document_to_musicxml(request.score_document)
        return {"validation_report": pipeline.musicxml_validator.validate_text(musicxml).to_report()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/score/light_validate")
def score_light_validate(request: LightValidateRequest) -> dict[str, object]:
    """Run lightweight validation for dirty Workbench measures."""

    try:
        report = _light_validate_score(request.score_document, request.dirty_measures)
        _append_score_event("light_validate", {"dirty_measures": request.dirty_measures, "warning_count": len(report["warnings"])})
        return {"validation_report": report}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/score/full_validate")
def score_full_validate(request: ScoreDocumentRequest) -> dict[str, object]:
    """Run full export validation for a ScoreDocument."""

    try:
        musicxml = score_document_to_musicxml(request.score_document)
        validation = pipeline.musicxml_validator.validate_text(musicxml).to_report()
        lightweight = _light_validate_score(request.score_document, [])
        validation["lightweight"] = lightweight
        _append_score_event("full_validate", {"score_id": request.score_document.get("score_id", ""), "valid": validation.get("valid_musicxml")})
        return {"validation_report": validation}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/score/render_preview_musicxml")
def score_render_preview_musicxml(request: ScoreDocumentRequest) -> dict[str, object]:
    """Return MusicXML for renderer adapters without writing an export."""

    try:
        musicxml = score_document_to_musicxml(request.score_document)
        event_count = sum(len(measure.get("events", [])) for measure in request.score_document.get("measures", []))
        validation = pipeline.musicxml_validator.validate_text(musicxml).to_report()
        return {
            "musicxml": musicxml,
            "validation_report": validation,
            "event_metadata_count": musicxml.count("sera-event-id:"),
            "score_event_count": event_count,
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/score/apply_operation")
def score_apply_operation(request: ApplyOperationRequest) -> dict[str, object]:
    """Apply one ScoreOperation and append operation history."""

    try:
        updated, operation = apply_score_operation(request.score_document, request.operation)
        history = record_operation(request.operation_history, operation)
        validation = pipeline.musicxml_validator.validate_text(score_document_to_musicxml(updated)).to_report()
        _append_score_event("apply_operation", operation)
        return {"score_document": updated, "operation": operation, "operation_history": history, "validation_report": validation}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/score/operation")
def score_operation_alias(request: ApplyOperationRequest) -> dict[str, object]:
    """V0.8 alias for applying one ScoreOperation."""

    return score_apply_operation(request)


@app.post("/score/batch_operations")
def score_batch_operations(request: BatchOperationsRequest) -> dict[str, object]:
    """Apply multiple ScoreOperations and append them to operation history."""

    try:
        updated, operations = apply_operations(request.score_document, request.operations)
        history = request.operation_history
        for operation in operations:
            history = record_operation(history, operation)
        validation = pipeline.musicxml_validator.validate_text(score_document_to_musicxml(updated)).to_report()
        _append_score_event("batch_operations", {"operation_count": len(operations)})
        return {"score_document": updated, "operations": operations, "operation_history": history, "validation_report": validation}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/score/undo")
def score_undo(request: HistoryRequest) -> dict[str, object]:
    """Undo the latest workbench operation."""

    updated, history = undo_last(request.score_document, request.operation_history)
    validation = pipeline.musicxml_validator.validate_text(score_document_to_musicxml(updated)).to_report()
    _append_score_event("undo", {"remaining": len(history.get("done", []))})
    return {"score_document": updated, "operation_history": history, "validation_report": validation}


@app.post("/score/redo")
def score_redo(request: HistoryRequest) -> dict[str, object]:
    """Redo the latest undone workbench operation."""

    updated, history = redo_last(request.score_document, request.operation_history)
    validation = pipeline.musicxml_validator.validate_text(score_document_to_musicxml(updated)).to_report()
    _append_score_event("redo", {"done": len(history.get("done", []))})
    return {"score_document": updated, "operation_history": history, "validation_report": validation}


@app.post("/score/agent_edit")
def score_agent_edit(request: AgentEditRequest) -> dict[str, object]:
    """Generate a previewable ScorePatch from an editing instruction."""

    edit_context = {
        "current_selection": request.current_selection,
        "recent_operations": request.recent_operations,
        "dirty_measures": request.dirty_measures,
        "validation_warnings": request.validation_warnings,
        "playback_position": request.playback_position,
        "selected_notes_summary": request.selected_notes_summary,
        "user_edit_intent_inferred": request.user_edit_intent_inferred,
        "preserve_user_edits_since_timestamp": request.preserve_user_edits_since_timestamp,
    }
    patch = score_editing_agent.create_patch(
        request.score_document,
        request.instruction,
        selected_range=request.selected_range,
        constraints=request.constraints,
        edit_context=edit_context,
    )
    preview = score_patch_service.preview_patch(
        request.score_document,
        patch,
        instruction=request.instruction,
        selected_range=request.selected_range,
        constraints=request.constraints,
    )
    _append_score_event("agent_edit", {"instruction": request.instruction, "patch": patch})
    pipeline.logger.append(
        {
            "run_id": f"score_edit_{uuid.uuid4().hex[:12]}",
            "event": "agent_score_edit",
            "instruction": request.instruction,
            "patch": patch,
            "prompt_alignment_score": preview.get("prompt_alignment_score", {}),
            "patch_validation_report": preview.get("patch_validation_report", {}),
            "agent_trace": score_editing_agent.last_trace,
            "manual_edit_context": edit_context,
        }
    )
    preview["agent_trace"] = score_editing_agent.last_trace
    return preview


@app.post("/score/preview_patch")
def score_preview_patch(request: PatchRequest) -> dict[str, object]:
    """Preview a ScorePatch without applying it."""

    return score_patch_service.preview_patch(
        request.score_document,
        request.patch,
        instruction=request.instruction,
        selected_range=request.selected_range,
        constraints=request.constraints,
    )


@app.post("/score/validate_patch")
def score_validate_patch(request: PatchRequest) -> dict[str, object]:
    """Validate a ScorePatch before applying it."""

    report = score_patch_service.validate_patch(
        request.score_document,
        request.patch,
        instruction=request.instruction,
        selected_range=request.selected_range,
        constraints=request.constraints,
    )
    return {"patch_validation_report": report}


@app.post("/score/apply_patch")
def score_apply_patch(request: PatchRequest) -> dict[str, object]:
    """Apply a ScorePatch if validation succeeds."""

    result = score_patch_service.apply_patch(
        request.score_document,
        request.patch,
        instruction=request.instruction,
        selected_range=request.selected_range,
        constraints=request.constraints,
    )
    _append_score_event("apply_patch", {"patch_id": result.get("patch", {}).get("patch_id"), "accepted": result.get("accepted")})
    return result


@app.post("/score/partial_apply_patch")
def score_partial_apply_patch(request: PartialPatchRequest) -> dict[str, object]:
    """Apply a selected subset of ScorePatch operations."""

    result = score_patch_service.partial_apply_patch(
        request.score_document,
        request.patch,
        operation_ids=request.operation_ids,
        operation_indexes=request.operation_indexes,
        apply_filter=request.apply_filter,
        instruction=request.instruction,
        selected_range=request.selected_range,
        constraints=request.constraints,
    )
    _append_score_event(
        "partial_apply_patch",
        {
            "patch_id": result.get("patch", {}).get("patch_id"),
            "original_patch_id": result.get("original_patch_id"),
            "accepted": result.get("accepted"),
            "rejected_operation_count": len(result.get("rejected_operations", [])),
        },
    )
    return result


@app.post("/score/reject_patch")
def score_reject_patch(request: PatchRequest) -> dict[str, object]:
    """Reject a ScorePatch and keep the current score unchanged."""

    result = score_patch_service.reject_patch(request.score_document, request.patch, reason=request.reason)
    _append_score_event("reject_patch", {"patch_id": result.get("patch", {}).get("patch_id"), "reason": request.reason})
    return result


@app.post("/score/explain_selection")
def score_explain_selection(request: ExplainSelectionRequest) -> dict[str, object]:
    """Explain a selected passage without modifying the score."""

    explanation = score_editing_agent.explain_selection(request.score_document, request.selected_range, request.question)
    _append_score_event("explain_selection", {"selected_range": request.selected_range, "question": request.question})
    pipeline.logger.append(
        {
            "run_id": f"score_explain_{uuid.uuid4().hex[:12]}",
            "event": "agent_score_explain",
            "selected_range": request.selected_range,
            "question": request.question,
            "explanation": explanation,
        }
    )
    return {"explanation": explanation}


@app.post("/score/generate_accompaniment")
def score_generate_accompaniment(request: AccompanimentRequest) -> dict[str, object]:
    """Generate a previewable fallback left-hand accompaniment patch."""

    patch = generate_left_hand_accompaniment_patch(request.score_document, request.selected_range, texture=request.texture)
    preview = score_patch_service.preview_patch(
        request.score_document,
        patch,
        instruction="Generate left-hand accompaniment",
        selected_range=request.selected_range,
        constraints={"preserve_harmony": True, "target_staff": "left_hand"},
    )
    _append_score_event("generate_accompaniment", {"texture": request.texture, "operation_count": len(patch.get("operations", []))})
    return preview


@app.post("/score/migrate_project")
def score_migrate_project(request: ProjectMigrationRequest) -> dict[str, object]:
    """Migrate an older .sera.json project payload to V0.8."""

    try:
        project = migrate_workbench_project(request.project)
        _append_score_event("migrate_project", {"score_id": project.get("score_document", {}).get("score_id", "")})
        return {"project": project, "summary": project_summary(project)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Project migration failed: {exc}") from exc


@app.post("/score/export_project_package")
def score_export_project_package(request: ProjectMigrationRequest) -> dict[str, object]:
    """Return and save a screenshot-ready V0.8 project package."""

    try:
        project = migrate_workbench_project(request.project)
        summary = project_summary(project)
        project_id = _safe_project_id(str(project.get("project_id") or summary.get("score_id") or f"sera_project_{uuid.uuid4().hex[:8]}"))
        path = PROJECT_ROOT / "data" / "projects" / f"{project_id}_package.sera.json"
        save_score_project(path, {"project": project, "summary": summary})
        _append_score_event("export_project_package", {"project_id": project_id, "path": str(path)})
        return {"project": project, "summary": summary, "path": str(path)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Project package export failed: {exc}") from exc


@app.post("/score/revert_last_agent_patch")
def score_revert_last_agent_patch(request: RevertAgentPatchRequest) -> dict[str, object]:
    """Remove the latest agent operation while replaying later manual edits."""

    done = list(request.operation_history.get("done", []))
    agent_index = next((index for index in range(len(done) - 1, -1, -1) if done[index].get("source") == "agent"), None)
    if agent_index is None:
        return {"score_document": request.score_document, "operation_history": request.operation_history, "reverted": False, "reason": "No agent operation found."}
    base_score = done[agent_index].get("before", {}).get("score_document") or request.score_document
    replay = [operation for operation in done[agent_index + 1 :] if operation.get("source") != "agent"]
    updated = replay_operations(base_score, replay)
    history = {"done": done[:agent_index] + replay, "undone": list(request.operation_history.get("undone", []))}
    validation = pipeline.musicxml_validator.validate_text(score_document_to_musicxml(updated)).to_report()
    _append_score_event("revert_last_agent_patch", {"removed_operation_id": done[agent_index].get("operation_id")})
    return {"score_document": updated, "operation_history": history, "validation_report": validation, "reverted": True}


@app.post("/score/continue_from_last_edit")
def score_continue_from_last_edit(request: ContinueFromLastEditRequest) -> dict[str, object]:
    """Ask the agent to continue from recent manual edits while preserving them."""

    edit_request = AgentEditRequest(
        score_document=request.score_document,
        instruction=request.instruction,
        selected_range=request.selected_range,
        constraints={**request.constraints, "preserve_manual_edits": True},
        recent_operations=request.recent_operations,
        selected_notes_summary={},
        current_selection={},
        user_edit_intent_inferred="continue from recent manual edit",
    )
    return score_agent_edit(edit_request)


@app.post("/score/save_project")
def score_save_project(request: SaveProjectRequest) -> dict[str, object]:
    """Save a self-contained .sera.json workbench project."""

    project_id = _safe_project_id(request.project_id or f"sera_project_{uuid.uuid4().hex[:10]}")
    path = PROJECT_ROOT / "data" / "projects" / f"{project_id}.sera.json"
    payload = {
        "project_id": project_id,
        "saved_at": datetime.now(UTC).isoformat(),
        **request.project,
    }
    save_score_project(path, payload)
    _append_score_event("save_project", {"project_id": project_id, "path": str(path)})
    return {"project_id": project_id, "path": str(path), "project": payload}


@app.post("/score/load_project")
def score_load_project(request: LoadProjectRequest) -> dict[str, object]:
    """Load a .sera.json workbench project by project id."""

    project_id = _safe_project_id(request.project_id)
    path = PROJECT_ROOT / "data" / "projects" / f"{project_id}.sera.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    project = load_score_project(path)
    _append_score_event("load_project", {"project_id": project_id})
    return {"project_id": project_id, "path": str(path), "project": project}


@app.post("/score/prompt_alignment")
def score_prompt_alignment_endpoint(request: PatchRequest) -> dict[str, object]:
    """Score a patch against prompt and preserve constraints."""

    return {
        "prompt_alignment_score": score_prompt_alignment(
            request.instruction,
            request.selected_range,
            request.constraints,
            request.patch,
        )
    }


@app.get("/score/render_capabilities")
def score_render_capabilities() -> dict[str, object]:
    """Return backend-visible workbench rendering/export capabilities."""

    package_path = PROJECT_ROOT / "frontend" / "package.json"
    dependencies: dict[str, Any] = {}
    if package_path.exists():
        package = json.loads(package_path.read_text(encoding="utf-8"))
        dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    return {
        "renderer_modes": ["auto", "osmd", "vexflow", "fallback"],
        "fallback_svg": True,
        "osmd_dependency_declared": "opensheetmusicdisplay" in dependencies,
        "vexflow_dependency_declared": "vexflow" in dependencies,
        "musescore_cli_available": bool(shutil.which("musescore") or shutil.which("MuseScore4")),
        "pdf_export_fallback": True,
    }


@app.get("/score/workbench_health")
def score_workbench_health() -> dict[str, object]:
    """Return Score Workbench readiness for the frontend and demos."""

    provider = create_llm_provider()
    return {
        "status": "ok",
        "score_schema_version": "0.6",
        "workbench_version": "0.8",
        "llm_provider": provider.provider,
        "llm_model": provider.model,
        "live_provider_available": provider.available(),
        "mock_fallback": True,
        "apis": [
            "/score/operation",
            "/score/batch_operations",
            "/score/light_validate",
            "/score/full_validate",
            "/score/render_preview_musicxml",
            "/score/agent_edit",
            "/score/validate_patch",
            "/score/partial_apply_patch",
            "/score/explain_selection",
            "/score/generate_accompaniment",
            "/score/migrate_project",
            "/score/export_project_package",
            "/score/revert_last_agent_patch",
            "/score/continue_from_last_edit",
            "/score/render_capabilities",
        ],
    }


@app.get("/experiments")
def experiments(limit: int = 25) -> dict[str, object]:
    """Return recent experiment logs."""

    return {"records": pipeline.logger.list_records(limit=limit)}


def _append_score_event(event_type: str, payload: dict[str, Any]) -> None:
    """Append a workbench operation/event log for research replay."""

    target = PROJECT_ROOT / "data" / "metadata" / "score_operations.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(UTC).isoformat(), "event_type": event_type, **payload}
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _light_validate_score(score_document: dict[str, Any], dirty_measures: list[int]) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    meter = str(score_document.get("global", {}).get("meter", "4/4"))
    try:
        beats, beat_type = [int(part) for part in meter.split("/", 1)]
        capacity = beats * (4 / beat_type)
    except (ValueError, TypeError):
        capacity = 4.0
        errors.append(f"Invalid meter: {meter}")
    targets = set(int(item) for item in dirty_measures or [])
    checked = 0
    for measure in score_document.get("measures", []):
        number = int(measure.get("number", 0))
        if targets and number not in targets:
            continue
        checked += 1
        if not measure.get("events"):
            warnings.append(f"Measure {number} has no editable events.")
            continue
        by_staff_voice: dict[tuple[str, int], float] = {}
        for event in measure.get("events", []):
            staff_voice = (str(event.get("staff", "right_hand")), int(event.get("voice", 1) or 1))
            end = float(event.get("offset", 0.0) or 0.0) + _duration_quarters(str(event.get("duration", "quarter")))
            by_staff_voice[staff_voice] = max(by_staff_voice.get(staff_voice, 0.0), end)
            if event.get("type") == "note" and not event.get("pitch"):
                errors.append(f"Measure {number} note {event.get('event_id')} is missing pitch.")
        for (staff, voice), used in by_staff_voice.items():
            if used > capacity + 0.001:
                errors.append(f"Measure {number} {staff} voice {voice} exceeds meter capacity.")
            elif used < capacity - 0.001:
                warnings.append(f"Measure {number} {staff} voice {voice} is underfilled by {round(capacity - used, 2)} quarters.")
    return {
        "valid": not errors,
        "valid_musicxml": not errors,
        "mode": "lightweight",
        "checked_measures": checked,
        "dirty_measures": sorted(targets),
        "warnings": warnings,
        "errors": errors,
    }


def _duration_quarters(duration: str) -> float:
    return {
        "whole": 4.0,
        "half": 2.0,
        "quarter": 1.0,
        "eighth": 0.5,
        "sixteenth": 0.25,
        "dotted_half": 3.0,
        "dotted_quarter": 1.5,
        "dotted_eighth": 0.75,
        "triplet_eighth": 1.0 / 3.0,
    }.get(duration, 1.0)


def _safe_project_id(value: str) -> str:
    """Keep project saves inside data/projects."""

    cleaned = "".join(char for char in value if char.isalnum() or char in {"_", "-", "."}).strip(".")
    if not cleaned:
        cleaned = f"sera_project_{uuid.uuid4().hex[:10]}"
    return cleaned[:120]

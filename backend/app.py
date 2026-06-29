"""FastAPI app for the Sera MVP."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from backend.pipeline import SeraPipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# TODO: move environment validation into a dedicated settings module when Sera
# grows more runtime configuration knobs.
load_dotenv(PROJECT_ROOT / ".env")
pipeline = SeraPipeline(PROJECT_ROOT)

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


@app.get("/health")
def health() -> dict[str, str]:
    """Return a small health response."""

    return {"status": "ok", "app": "Sera", "version": "0.2.0"}


@app.post("/generate")
def generate(request: GenerateRequest) -> dict[str, object]:
    """Generate a score from a natural-language prompt."""

    return pipeline.generate(request.prompt)


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


@app.get("/experiments")
def experiments(limit: int = 25) -> dict[str, object]:
    """Return recent experiment logs."""

    return {"records": pipeline.logger.list_records(limit=limit)}

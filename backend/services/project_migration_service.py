"""Workbench project migration helpers for Sera V0.8."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.services.score_document_service import normalize_score_document


def migrate_workbench_project(project: dict[str, Any]) -> dict[str, Any]:
    """Return a self-contained V0.8 .sera.json project payload."""

    source = dict(project or {})
    score = normalize_score_document(
        source.get("score_document")
        or source.get("ScoreDocument")
        or source.get("scoreDocument")
        or {}
    )
    score.setdefault("metadata", {})
    score["metadata"]["workbench_version"] = "0.8"
    history = source.get("operation_history") or source.get("OperationHistory") or source.get("operationHistory") or {}
    return {
        "project_version": "0.8",
        "migrated_at": datetime.now(UTC).isoformat(),
        "score_document": score,
        "operation_history": {
            "done": list(history.get("done", [])),
            "undone": list(history.get("undone", [])),
        },
        "agent_patch_history": list(source.get("agent_patch_history") or source.get("AgentPatchHistory") or []),
        "original_prompt": source.get("original_prompt") or source.get("OriginalPrompt") or "",
        "composition_plan": source.get("composition_plan") or source.get("CompositionPlan") or {},
        "validation_reports": list(source.get("validation_reports") or source.get("ValidationReports") or []),
        "export_metadata": source.get("export_metadata") or source.get("ExportMetadata") or {},
        "experiment_metadata": source.get("experiment_metadata") or source.get("ExperimentMetadata") or {},
    }


def project_summary(project: dict[str, Any]) -> dict[str, Any]:
    """Return a screenshot-ready project summary."""

    migrated = migrate_workbench_project(project)
    score = migrated["score_document"]
    operations = migrated["operation_history"]["done"]
    patches = migrated["agent_patch_history"]
    return {
        "project_version": migrated["project_version"],
        "score_id": score.get("score_id", ""),
        "title": score.get("title", ""),
        "measure_count": len(score.get("measures", [])),
        "event_count": sum(len(measure.get("events", [])) for measure in score.get("measures", [])),
        "operation_count": len(operations),
        "agent_patch_count": len(patches),
        "last_saved_or_migrated": migrated.get("migrated_at", ""),
    }

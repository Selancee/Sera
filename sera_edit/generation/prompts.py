"""Versioned, condition-separated prompts and compact score context."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.services.score_document_service import score_document_to_musicxml
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.domain.score_scope import ScoreScope, iter_event_contexts


PROMPTS = {
    "full_rewrite": (
        "full_rewrite_v1.1",
        "Edit the supplied MusicXML according to the instruction. Return only the complete modified MusicXML. Preserve unspecified content.",
    ),
    "patch_only": (
        "patch_only_v1.1",
        "Return only a ScorePatch 1.0.0 JSON object. Use the supplied stable event IDs and target scope. Do not return MusicXML, prose, or Markdown.",
    ),
    "sera_full": (
        "sera_patch_v1.1",
        "Return only a source-bound ScorePatch 1.0.0 JSON object. Stay inside target scope, do not alter protected scope, satisfy explicit constraints, and return a refusal object for conflicts or unsupported requests. Do not return Markdown.",
    ),
    "sera_repair": (
        "sera_repair_v1.0",
        "Repair the candidate into one valid source-bound ScorePatch 1.0.0 JSON object. Change only what the listed validation errors require. Preserve target and protected scopes. Return a refusal object if the instruction is conflicting or unsupported. Return JSON only.",
    ),
}


def prompt_metadata(condition: str) -> dict[str, str]:
    """Return prompt version, body, and stable hash for manifests."""

    version, prompt = PROMPTS[condition]
    return {"prompt_version": version, "prompt": prompt, "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest()}


@lru_cache(maxsize=1)
def score_patch_schema() -> dict[str, Any]:
    """Load the versioned benchmark schema once."""

    path = Path(__file__).resolve().parents[2] / "benchmark" / "schemas" / "score_patch.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def sera_response_schema() -> dict[str, Any]:
    """Return a structured-output schema accepting a patch or explicit refusal."""

    patch = json.loads(json.dumps(score_patch_schema()))
    definitions = patch.pop("$defs", {})
    patch.pop("$schema", None)
    patch.pop("$id", None)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "SeraEdit patch or refusal response",
        "oneOf": [
            patch,
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["refusal", "reason"],
                "properties": {
                    "refusal": {"const": True},
                    "reason": {"type": "string", "minLength": 1},
                },
            },
        ],
        "$defs": definitions,
    }


def compact_score_context(score: dict[str, Any], target_scope: dict[str, Any]) -> dict[str, Any]:
    """Return target events plus one neighboring measure without sending unrelated score detail."""

    scope = ScoreScope.from_dict(target_scope)
    selected = scope.select(score)
    target_measures = {context.measure for context in selected} or set(scope.measures)
    if scope.whole_score:
        included_measures = {int(measure.get("number", 0)) for measure in score.get("measures") or []}
    else:
        included_measures = {
            measure
            for target in target_measures
            for measure in (target - 1, target, target + 1)
            if measure > 0
        }
    events = []
    for context in iter_event_contexts(score):
        if context.measure not in included_measures:
            continue
        event = context.event
        events.append(
            {
                "event_id": context.event_id,
                "measure": context.measure,
                "part": context.part_id,
                "staff": context.staff,
                "voice": context.voice,
                "offset": str(context.offset),
                "type": event.get("type"),
                "pitch": event.get("pitch"),
                "duration": event.get("duration"),
                "dynamic": event.get("dynamic"),
                "articulations": event.get("articulations") or [],
                "tie": event.get("tie"),
                "slur": event.get("slur"),
                "grace": bool(event.get("grace")),
                "is_chord_tone": bool(event.get("is_chord_tone")),
            }
        )
    return {
        "score_id": score.get("score_id"),
        "source_fingerprint": score_fingerprint(score),
        "global": score.get("global") or {},
        "included_measures": sorted(included_measures),
        "events": events,
    }


def build_condition_messages(
    condition: str,
    task: dict[str, Any],
    source_score: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    """Build condition-specific messages while preserving experimental boundaries."""

    prompt = prompt_metadata(condition)
    if condition == "full_rewrite":
        user_payload = f"Instruction:\n{task['instruction_en']}\n\nOriginal MusicXML:\n{score_document_to_musicxml(source_score)}"
        return [
            {"role": "system", "content": prompt["prompt"]},
            {"role": "user", "content": user_payload},
        ], None
    payload: dict[str, Any] = {
        "instruction": task["instruction_en"],
        "target_scope": task["target_scope"],
        "score_context": compact_score_context(source_score, task["target_scope"]),
        "score_patch_schema": score_patch_schema(),
    }
    if condition == "sera_full":
        payload.update(
            {
                "protected_scope": task["protected_scope"],
                "expected_constraints": task["expected_constraints"],
                "expected_status": task["expected_status"],
                "unsupported_reason": task.get("unsupported_reason"),
            }
        )
    return [
        {"role": "system", "content": prompt["prompt"]},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
    ], sera_response_schema() if condition == "sera_full" else score_patch_schema()


def build_repair_messages(
    task: dict[str, Any],
    source_score: dict[str, Any],
    candidate: Any,
    validation_errors: list[dict[str, Any]],
    *,
    attempt: int,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Build one bounded Condition C repair request with full safety context."""

    prompt = prompt_metadata("sera_repair")
    payload = {
        "repair_attempt": attempt,
        "instruction": task["instruction_en"],
        "candidate": candidate,
        "validation_errors": validation_errors,
        "target_scope": task["target_scope"],
        "protected_scope": task["protected_scope"],
        "expected_constraints": task["expected_constraints"],
        "expected_status": task["expected_status"],
        "source_fingerprint": score_fingerprint(source_score),
        "score_context": compact_score_context(source_score, task["target_scope"]),
        "score_patch_schema": score_patch_schema(),
    }
    return [
        {"role": "system", "content": prompt["prompt"]},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
    ], sera_response_schema()

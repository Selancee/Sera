"""Schema-constrained Agentic Score Editing for Sera V0.8."""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from backend.llm.provider_factory import create_llm_provider
from backend.services.score_patch_validation_service import validate_score_patch_schema


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_VERSION = "score_editing_agent_v0.8"


class ScoreEditingAgent:
    """Create previewable ScorePatch JSON from a score edit instruction.

    The agent attempts a schema-constrained provider call when configured, then
    repairs malformed JSON once, and finally falls back to the deterministic
    mock planner so the Workbench remains API-key-free.
    """

    def __init__(self) -> None:
        self.last_trace: dict[str, Any] = {}

    def create_patch(
        self,
        score_document: dict[str, Any],
        instruction: str,
        selected_range: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
        edit_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a local, previewable ScorePatch."""

        selected_range = selected_range or self._default_range(score_document)
        constraints = constraints or {}
        edit_context = edit_context or {}
        provider = create_llm_provider()
        trace: dict[str, Any] = {
            "provider": provider.provider,
            "model": provider.model,
            "prompt_version": PROMPT_VERSION,
            "raw_response": "",
            "parsed_patch": None,
            "schema_errors": [],
            "fallback_reason": "",
            "latency_ms": 0.0,
        }
        if provider.available():
            prompt = _read_prompt("backend/prompts/score_editing_agent.md")
            payload = {
                "instruction": instruction,
                "selected_range": selected_range,
                "constraints": constraints,
                "current_score_summary": self._score_summary(score_document),
                "current_score_excerpt": self._score_excerpt(score_document, selected_range),
                "manual_edit_context": edit_context,
                "score_patch_schema": "backend/schemas/score_patch.schema.json",
            }
            result = provider.complete_json(prompt, json.dumps(payload, ensure_ascii=False))
            trace.update(
                {
                    "provider": result.provider,
                    "model": result.model,
                    "raw_response": result.text,
                    "latency_ms": round(result.latency_ms, 3),
                }
            )
            patch, errors = self._parse_provider_patch(result.text, instruction, selected_range)
            if errors:
                repair = provider.complete_json(
                    _read_prompt("backend/prompts/score_patch_repair.md"),
                    json.dumps(
                        {
                            "raw_response": result.text,
                            "schema_errors": errors,
                            "instruction": instruction,
                            "selected_range": selected_range,
                            "constraints": constraints,
                        },
                        ensure_ascii=False,
                    ),
                )
                patch, errors = self._parse_provider_patch(repair.text, instruction, selected_range)
                trace["raw_response"] = f"{result.text}\n\n--- repair ---\n{repair.text}"
                trace["latency_ms"] = round(float(trace["latency_ms"]) + repair.latency_ms, 3)
            if patch and not errors:
                trace["parsed_patch"] = patch
                self.last_trace = trace
                return patch
            trace["schema_errors"] = errors
            trace["fallback_reason"] = result.error or "provider patch failed schema validation"
        else:
            trace["fallback_reason"] = "provider unavailable or API key missing"

        patch = self._create_mock_patch(score_document, instruction, selected_range, constraints, edit_context)
        trace["parsed_patch"] = patch
        self.last_trace = trace
        return patch

    def explain_selection(
        self,
        score_document: dict[str, Any],
        selected_range: dict[str, Any] | None = None,
        question: str = "",
    ) -> dict[str, Any]:
        """Explain the selected score region without producing a patch."""

        selected_range = selected_range or self._default_range(score_document)
        provider = create_llm_provider()
        if provider.available():
            payload = {
                "task": "explain selected passage without modifying the score",
                "selected_range": selected_range,
                "question": question,
                "current_score_excerpt": self._score_excerpt(score_document, selected_range),
            }
            result = provider.complete_json(
                "Return only JSON with summary, harmony_analysis, melodic_analysis, rhythmic_analysis, difficulty_notes, suggested_edits.",
                json.dumps(payload, ensure_ascii=False),
            )
            parsed = _parse_json_object(result.text)
            if isinstance(parsed, dict):
                return _normalize_explanation(parsed)
        return self._mock_explanation(score_document, selected_range, question)

    def _create_mock_patch(
        self,
        score_document: dict[str, Any],
        instruction: str,
        selected_range: dict[str, Any],
        constraints: dict[str, Any],
        edit_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a deterministic fallback ScorePatch."""

        edit_context = edit_context or {}
        measures = score_document.get("measures", [])
        start = int(selected_range.get("start_measure", 1))
        end = int(selected_range.get("end_measure", start))
        text = instruction.lower()
        operations: list[dict[str, Any]] = []
        patch_type = "transform_notes"
        matched = []
        risks = []

        if "cadence" in text or "ending" in text or "终止" in instruction:
            patch_type = "add_cadence"
            operations.append(
                {
                    "source": "agent",
                    "type": "add_cadence",
                    "target": {"start_measure": end, "end_measure": end, "measure": end, "staff": "right_hand"},
                    "after": {"cadence": "authentic"},
                    "description": "Add an authentic cadence to the selected ending.",
                }
            )
            matched.append("cadence")
        elif "simpl" in text or "beginner" in text or "降低难度" in instruction:
            patch_type = "simplify"
            operations.append(
                {
                    "source": "agent",
                    "type": "simplify_rhythm",
                    "target": {"start_measure": start, "end_measure": end},
                    "after": {"duration": "quarter"},
                    "description": "Simplify rhythms in the selected passage.",
                }
            )
            matched.append("difficulty")
        elif "density" in text or "rhythm" in text or "节奏" in instruction:
            patch_type = "transform_notes"
            operations.append(
                {
                    "source": "agent",
                    "type": "humanize_rhythm",
                    "target": {"start_measure": start, "end_measure": end},
                    "after": {"duration": "eighth"},
                    "description": "Increase rhythmic surface activity in the selected measures.",
                }
            )
            matched.append("rhythmic density")
        elif "left" in text or "accompaniment" in text or "左手" in instruction:
            patch_type = "update_texture"
            for number in range(start, end + 1):
                operations.append(
                    {
                        "source": "agent",
                        "type": "insert_note",
                        "target": {"measure": number, "staff": "left_hand"},
                        "after": {"pitch": "C3", "duration": "eighth", "offset": 0.5, "staff": "left_hand", "dynamic": "mp"},
                        "description": "Add a flowing left-hand accompaniment tone.",
                    }
                )
            matched.append("accompaniment")
            if constraints.get("preserve_harmony") is False:
                risks.append("harmony may need manual review")
        else:
            patch_type = "transform_notes"
            operations.append(
                {
                    "source": "agent",
                    "type": "transpose_selection",
                    "target": {"start_measure": start, "end_measure": end},
                    "after": {"semitones": -1 if "sad" in text or "忧郁" in instruction else 2},
                    "description": "Apply a small melodic transformation to the selected passage.",
                }
            )
            matched.append("melodic expression")

        if constraints.get("preserve_melody") and any(op["type"] in {"transpose_selection", "add_cadence"} for op in operations):
            risks.append("preserve_melody requested; melodic operations are intentionally minimal")
        recent_event_ids = _recent_manual_event_ids(edit_context)
        explicit_overwrite = any(word in instruction.lower() for word in ["overwrite", "replace my edit", "ignore my edit"]) or "覆盖" in instruction
        if recent_event_ids and (constraints.get("preserve_manual_edits", True) or edit_context.get("preserve_user_edits_since_timestamp")) and not explicit_overwrite:
            for operation in operations:
                target = operation.setdefault("target", {})
                if operation.get("type") in {"transpose_selection", "simplify_rhythm", "humanize_rhythm", "quantize_rhythm", "regenerate_selected_measures"}:
                    target["exclude_event_ids"] = sorted(recent_event_ids)
            matched.append("preserved recent manual edits")
            risks.append("recent user-edited events were excluded from broad agent operations")
        return {
            "patch_id": f"patch_{uuid.uuid4().hex[:12]}",
            "patch_type": patch_type,
            "target_range": {"start_measure": start, "end_measure": end},
            "operations": operations,
            "rationale": "The patch changes only the selected passage and keeps the rest of the ScoreDocument unchanged.",
            "expected_effect": self._expected_effect(patch_type),
            "prompt_alignment": {
                "instruction": instruction,
                "matched_aspects": matched,
                "risk_aspects": risks,
            },
            "validation_expectations": {
                "should_preserve_measure_count": patch_type != "replace_measures",
                "should_preserve_meter": True,
                "should_preserve_harmony": bool(constraints.get("preserve_harmony", False)),
            },
        }

    def _parse_provider_patch(
        self,
        text: str,
        instruction: str,
        selected_range: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, list[str]]:
        parsed = _parse_json_object(text)
        if not isinstance(parsed, dict):
            return None, ["provider response was not a JSON object"]
        patch = parsed.get("patch") if isinstance(parsed.get("patch"), dict) else parsed
        patch = self._normalize_patch(patch, instruction, selected_range)
        valid, errors = validate_score_patch_schema(patch)
        return (patch if valid else None), errors

    def _normalize_patch(
        self,
        patch: dict[str, Any],
        instruction: str,
        selected_range: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(patch or {})
        normalized.setdefault("patch_id", f"patch_{uuid.uuid4().hex[:12]}")
        normalized.setdefault("patch_type", "no_op" if not normalized.get("operations") else "transform_notes")
        normalized.setdefault(
            "target_range",
            {
                "start_measure": int(selected_range.get("start_measure", 1)),
                "end_measure": int(selected_range.get("end_measure", selected_range.get("start_measure", 1))),
            },
        )
        normalized.setdefault("operations", [])
        normalized.setdefault("rationale", "Provider returned a minimal local score edit.")
        normalized.setdefault("expected_effect", "The selected passage is adjusted while preserving the surrounding score.")
        normalized.setdefault("prompt_alignment", {"instruction": instruction, "matched_aspects": [], "risk_aspects": []})
        normalized.setdefault(
            "validation_expectations",
            {
                "should_preserve_measure_count": True,
                "should_preserve_meter": True,
                "should_preserve_harmony": False,
            },
        )
        return normalized

    def _default_range(self, score_document: dict[str, Any]) -> dict[str, int]:
        measures = score_document.get("measures", [])
        return {"start_measure": 1, "end_measure": min(4, max(1, len(measures)))}

    def _score_summary(self, score_document: dict[str, Any]) -> dict[str, Any]:
        measures = score_document.get("measures", [])
        return {
            "score_id": score_document.get("score_id", ""),
            "title": score_document.get("title", ""),
            "global": score_document.get("global", {}),
            "measure_count": len(measures),
            "event_count": sum(len(measure.get("events", [])) for measure in measures),
        }

    def _score_excerpt(self, score_document: dict[str, Any], selected_range: dict[str, Any]) -> dict[str, Any]:
        start = int(selected_range.get("start_measure", 1))
        end = int(selected_range.get("end_measure", start))
        return {
            "measures": [
                measure
                for measure in score_document.get("measures", [])
                if start <= int(measure.get("number", 0)) <= end
            ]
        }

    def _mock_explanation(
        self,
        score_document: dict[str, Any],
        selected_range: dict[str, Any],
        question: str = "",
    ) -> dict[str, Any]:
        excerpt = self._score_excerpt(score_document, selected_range).get("measures", [])
        event_count = sum(len(measure.get("events", [])) for measure in excerpt)
        harmonies = [str(measure.get("harmony", "I")) for measure in excerpt]
        return {
            "summary": f"Measures {selected_range.get('start_measure')}-{selected_range.get('end_measure')} contain {event_count} editable events.",
            "harmony_analysis": f"Harmony labels: {', '.join(harmonies) if harmonies else 'none'}.",
            "melodic_analysis": "The mock explanation identifies the selected melody from note events and keeps edits separate from analysis.",
            "rhythmic_analysis": "Rhythm is summarized from event durations; use the density tools for edit suggestions.",
            "difficulty_notes": "Difficulty estimate is heuristic in mock mode and should be reviewed by the user.",
            "suggested_edits": [
                "Preview a small local patch before applying changes.",
                "Use preserve constraints when asking the Agent to edit.",
            ],
            "question": question,
        }

    @staticmethod
    def _expected_effect(patch_type: str) -> str:
        return {
            "add_cadence": "A clearer phrase ending with dominant-to-tonic closure.",
            "simplify": "A more beginner-friendly passage with steadier durations.",
            "update_texture": "A more active accompaniment while preserving the selected range.",
            "transform_notes": "A local melodic or rhythmic variation without replacing the whole score.",
        }.get(patch_type, "A local score edit.")


def _read_prompt(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _parse_json_object(text: str) -> Any:
    clean = (text or "").strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _normalize_explanation(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": str(data.get("summary", "")),
        "harmony_analysis": str(data.get("harmony_analysis", "")),
        "melodic_analysis": str(data.get("melodic_analysis", "")),
        "rhythmic_analysis": str(data.get("rhythmic_analysis", "")),
        "difficulty_notes": str(data.get("difficulty_notes", "")),
        "suggested_edits": list(data.get("suggested_edits") or []),
    }


def _recent_manual_event_ids(edit_context: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for operation in edit_context.get("recent_operations") or []:
        if operation.get("source") != "user":
            continue
        target = operation.get("target") or {}
        event_id = target.get("event_id")
        if event_id:
            ids.add(str(event_id))
    selected = edit_context.get("selected_notes_summary") or edit_context.get("current_selection") or {}
    for event_id in selected.get("event_ids") or []:
        if event_id:
            ids.add(str(event_id))
    return ids

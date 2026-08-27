"""Privacy-bounded local audit trail for Composer planning decisions."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sera_edit.domain.fingerprints import score_fingerprint


_WRITE_LOCK = threading.Lock()


def default_trace_path() -> Path:
    """Return a stable per-user path that survives frozen-backend temp cleanup."""

    override = os.getenv("SERA_COMPOSER_TRACE_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    root = Path(local_app_data) if local_app_data else Path.home() / ".sera"
    return root / "Sera" / "composer_runs.v0.4.jsonl"


class ComposerRunTraceStore:
    """Append and read bounded traces without storing MusicXML or event pitches."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_trace_path()

    def record(
        self,
        *,
        score_document: dict[str, Any],
        brief: str,
        target_scope: dict[str, Any],
        protected_scope: dict[str, Any],
        planner_mode: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        created_at = datetime.now(UTC).isoformat()
        planner = dict(result.get("planner") or {})
        plan = dict(result.get("plan") or {})
        run_identity = json.dumps(
            {
                "created_at": created_at,
                "score_fingerprint": score_fingerprint(score_document),
                "brief": brief,
                "planner": planner,
                "plan_id": plan.get("plan_id"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        trace_id = "composer_run_" + hashlib.sha256(run_identity.encode("utf-8")).hexdigest()[:20]
        texture = dict(result.get("texture_analysis") or {})
        event = {
            "schema_version": "0.4.0",
            "trace_id": trace_id,
            "created_at": created_at,
            "brief": brief[:8000],
            "planner_mode": planner_mode,
            "source": {
                "score_id": str(score_document.get("score_id") or ""),
                "fingerprint": score_fingerprint(score_document),
                "target_scope": target_scope,
                "protected_scope": protected_scope,
            },
            "result": {
                "status": result.get("status"),
                "reason": result.get("reason"),
                "planner": planner,
                "plan": {key: value for key, value in plan.items() if key != "brief"},
                "knowledge": {
                    "knowledge_base_id": (result.get("style_knowledge") or {}).get("knowledge_base_id"),
                    "schema_version": (result.get("style_knowledge") or {}).get("schema_version"),
                    "query": (result.get("style_knowledge") or {}).get("query"),
                    "selected_rule_ids": [
                        item.get("rule_id") for item in (result.get("style_knowledge") or {}).get("matched_rules") or []
                    ],
                    "retrieval": (result.get("style_knowledge") or {}).get("retrieval"),
                },
                "texture_analysis": {
                    key: texture.get(key)
                    for key in (
                        "analysis_version",
                        "classifier",
                        "texture",
                        "confidence",
                        "evidence",
                        "voice_count",
                        "attack_alignment_ratio",
                        "homorhythmic_similarity",
                        "rhythmic_independence",
                        "register_separation_semitones",
                        "fingerprint",
                    )
                },
                "phrase_analysis": _phrase_summary(result.get("phrase_analysis")),
                "search_summary": result.get("search_summary"),
                "candidate_reviews": [
                    {
                        "candidate_id": candidate.get("candidate_id"),
                        "rank": candidate.get("rank"),
                        "review": {
                            key: (candidate.get("review") or {}).get(key)
                            for key in (
                                "status",
                                "overall_score",
                                "theory_score",
                                "motif_score",
                                "phrase_score",
                                "style_score",
                                "playability_score",
                                "melody_expectation_score",
                                "source_melody_expectation_score",
                                "melody_expectation_delta",
                                "melody_expectation_preservation",
                                "texture_structure_preserved",
                                "changed_event_count",
                            )
                        },
                    }
                    for candidate in result.get("candidates") or []
                ],
                "failure_analysis": result.get("failure_analysis"),
            },
            "privacy": {
                "local_only": True,
                "stores_musicxml": False,
                "stores_note_or_event_content": False,
                "stores_api_key": False,
                "stores_brief": True,
            },
        }
        with _WRITE_LOCK:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return {"trace_id": trace_id, "created_at": created_at, "persisted": True}

    def latest(self) -> dict[str, Any] | None:
        """Return the newest valid trace, ignoring partial or malformed lines."""

        if not self.path.exists():
            return None
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        for line in reversed(lines):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("schema_version") == "0.4.0":
                return payload
        return None


def _phrase_summary(payload: object) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    motif = payload.get("source_motif") or {}
    return {
        "analysis_version": payload.get("analysis_version"),
        "selected_note_count": payload.get("selected_note_count"),
        "measure_count": payload.get("measure_count"),
        "primary_voice_id": payload.get("primary_voice_id"),
        "source_motif": {
            "contour": motif.get("contour"),
            "interval_signs": motif.get("interval_signs"),
        },
        "fingerprint": payload.get("fingerprint"),
    }

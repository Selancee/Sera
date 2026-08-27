"""Local, privacy-preserving candidate preference feedback for Composer V0.2."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any


PREFERENCE_DIMENSIONS = ("motif", "phrase", "style", "harmony", "playability")
REVIEW_KEYS = {
    "motif": "motif_score",
    "phrase": "phrase_score",
    "style": "style_score",
    "harmony": "theory_score",
    "playability": "playability_score",
}
_WRITE_LOCK = threading.Lock()


def default_feedback_path() -> Path:
    """Return a per-user local path outside the repository."""

    override = os.getenv("SERA_COMPOSER_FEEDBACK_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    root = Path(local_app_data) if local_app_data else Path.home() / ".sera"
    return root / "Sera" / "composer_feedback.v0.2.jsonl"


class ComposerPreferenceStore:
    """Append idempotent local preference events and derive a compact profile."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_feedback_path()

    def record(
        self,
        *,
        comparison_id: str,
        plan_id: str,
        style_family: str,
        selected_candidate_id: str,
        rejected_candidate_ids: list[str],
        selected_review: dict[str, Any],
        reasons: list[str] | None = None,
    ) -> dict[str, Any]:
        """Record one candidate preference without storing score notes or user identity."""

        normalized_reasons = sorted({reason for reason in (reasons or []) if reason in PREFERENCE_DIMENSIONS})
        feedback_id = "pref_" + hashlib.sha256(
            f"{comparison_id}:{selected_candidate_id}".encode("utf-8")
        ).hexdigest()[:20]
        event = {
            "schema_version": "0.2.0",
            "feedback_id": feedback_id,
            "created_at": datetime.now(UTC).isoformat(),
            "comparison_id": comparison_id,
            "plan_id": plan_id,
            "style_family": style_family,
            "selected_candidate_id": selected_candidate_id,
            "rejected_candidate_ids": sorted(set(rejected_candidate_ids)),
            "reasons": normalized_reasons,
            "selected_metrics": _metric_summary(selected_review),
            "privacy": {"stores_score_content": False, "stores_user_identity": False},
        }
        with _WRITE_LOCK:
            existing = self.load_events()
            if any(item.get("feedback_id") == feedback_id for item in existing):
                return {"recorded": False, "feedback_id": feedback_id, "preference_profile": build_preference_profile(existing)}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            existing.append(event)
        return {"recorded": True, "feedback_id": feedback_id, "preference_profile": build_preference_profile(existing)}

    def load_events(self, *, limit: int = 1000) -> list[dict[str, Any]]:
        """Load valid local events, ignoring malformed lines without failing Composer."""

        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()[-max(1, limit) :]
        except OSError:
            return []
        for line in lines:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("schema_version") == "0.2.0":
                events.append(item)
        return events

    def profile(self) -> dict[str, Any]:
        """Return an aggregate profile with no raw comments or score content."""

        return build_preference_profile(self.load_events())


def build_preference_profile(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate selected-candidate metrics into auditable preference targets."""

    targets: dict[str, list[float]] = {dimension: [] for dimension in PREFERENCE_DIMENSIONS}
    reasons = {dimension: 0 for dimension in PREFERENCE_DIMENSIONS}
    styles: dict[str, int] = {}
    for event in events:
        style = str(event.get("style_family", ""))
        if style:
            styles[style] = styles.get(style, 0) + 1
        metrics = event.get("selected_metrics") or {}
        for dimension in PREFERENCE_DIMENSIONS:
            value = metrics.get(dimension)
            if isinstance(value, (int, float)):
                targets[dimension].append(max(0.0, min(1.0, float(value))))
        for reason in event.get("reasons") or []:
            if reason in reasons:
                reasons[reason] += 1
    dimension_targets = {
        dimension: round(mean(values), 4)
        for dimension, values in targets.items()
        if values
    }
    return {
        "schema_version": "0.2.0",
        "feedback_count": len(events),
        "dimension_targets": dimension_targets,
        "reason_counts": reasons,
        "preferred_styles": dict(sorted(styles.items(), key=lambda item: (-item[1], item[0]))),
        "active": bool(events),
        "privacy": {"local_only": True, "stores_score_content": False, "stores_user_identity": False},
    }


def preference_match_score(review: dict[str, Any], profile: dict[str, Any] | None) -> float:
    """Score proximity to the user's selected-candidate metric centroid."""

    targets = (profile or {}).get("dimension_targets") or {}
    if not targets:
        return 0.5
    similarities: list[float] = []
    reason_counts = (profile or {}).get("reason_counts") or {}
    weights: list[float] = []
    for dimension, target in targets.items():
        review_key = REVIEW_KEYS.get(dimension)
        value = review.get(review_key) if review_key else None
        if not isinstance(value, (int, float)) or not isinstance(target, (int, float)):
            continue
        similarities.append(max(0.0, 1.0 - abs(float(value) - float(target))))
        weights.append(1.0 + float(reason_counts.get(dimension, 0)))
    if not similarities:
        return 0.5
    return sum(score * weight for score, weight in zip(similarities, weights, strict=True)) / sum(weights)


def _metric_summary(review: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for dimension, review_key in REVIEW_KEYS.items():
        value = review.get(review_key)
        if isinstance(value, (int, float)):
            result[dimension] = round(max(0.0, min(1.0, float(value))), 4)
    return result

"""Traceable local review workflow for benchmark compliance and aesthetics gates."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import threading
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

from backend.services.score_document_service import score_document_to_musicxml
from backend.services.musicxml_voice_service import local_voice_from_musicxml
from evaluation.benchmark_io import load_task
from sera_edit.execution.diff_engine import score_diff


REVIEW_SCHEMA_VERSION = "1.0.0"
REVIEW_DECISIONS = {"compliant", "needs_revision", "exclude"}
REVIEW_ROLES = {"primary", "secondary"}
ISSUE_CODES = {
    "instruction_ambiguous",
    "target_scope_wrong",
    "protected_scope_wrong",
    "gold_patch_wrong",
    "expected_output_wrong",
    "refusal_label_wrong",
    "constraint_wrong",
    "musically_implausible",
    "host_render_issue",
    "other",
}
DIMENSION_KEYS = {
    "instruction_clarity",
    "scope_correctness",
    "gold_correctness",
    "musical_validity",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(*payloads: Any) -> str:
    raw = json.dumps(payloads, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _review_storage_root() -> Path:
    configured = os.getenv("SERA_REVIEW_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    runtime = os.getenv("SERA_RUNTIME_DIR", "").strip()
    if runtime:
        return (Path(runtime).expanduser().resolve().parent / "research_reviews").resolve()
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return (Path(local_app_data) / "Sera" / "research_reviews").resolve()
    return (Path.home() / ".sera" / "research_reviews").resolve()


def _display_instruction(task: dict[str, Any]) -> dict[str, str]:
    english = str(task.get("instruction_en") or "").strip()
    chinese = str(task.get("instruction_zh") or "").strip()
    if not chinese or "\ufffd" in chinese:
        chinese = ""
    return {"en": english, "zh": chinese}


def _event_brief(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if event is None:
        return None
    fields = (
        "type",
        "pitch",
        "duration",
        "offset",
        "staff",
        "voice",
        "dynamic",
        "articulation",
        "tie",
        "slur",
    )
    return {key: event.get(key) for key in fields if key in event and event.get(key) not in (None, "", [])}


def _diff_rows(diff: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in diff.get("changed", []):
        rows.append(
            {
                "kind": "changed",
                "event_id": item.get("event_id", ""),
                "measure": (item.get("after_location") or item.get("before_location") or {}).get("measure"),
                "fields": item.get("changed_fields", []),
                "before": _event_brief(item.get("before")),
                "after": _event_brief(item.get("after")),
            }
        )
    for kind in ("added", "deleted"):
        for item in diff.get(kind, []):
            event = item.get("after") if kind == "added" else item.get("before")
            rows.append(
                {
                    "kind": kind,
                    "event_id": item.get("event_id", ""),
                    "measure": item.get("measure"),
                    "fields": [],
                    "before": _event_brief(event) if kind == "deleted" else None,
                    "after": _event_brief(event) if kind == "added" else None,
                }
            )
    for field, change in (diff.get("global_changes") or {}).items():
        rows.append(
            {
                "kind": "global",
                "event_id": field,
                "measure": None,
                "fields": [field],
                "before": {field: change.get("before")},
                "after": {field: change.get("after")},
            }
        )
    return rows


def _exported_dynamic_marks(score_document: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the dynamics that a notation host will visibly receive.

    ScoreDocument stores an effective dynamic on every event, while MusicXML
    serializes only changes in that persistent state. Human reviewers need
    this second view because one event-level edit may legitimately require a
    following reset mark in MuseScore.
    """

    root = ET.fromstring(score_document_to_musicxml(score_document))
    marks: list[dict[str, Any]] = []
    for part in root.findall("./part"):
        for measure in part.findall("./measure"):
            measure_number = int(measure.get("number") or 0)
            for note in measure.findall("./note"):
                dynamics = note.find("./notations/dynamics")
                if dynamics is None or not list(dynamics):
                    continue
                technical = note.find("./notations/technical/other-technical")
                technical_text = str(technical.text or "") if technical is not None else ""
                event_id = technical_text.removeprefix("sera-event-id:") if technical_text.startswith("sera-event-id:") else ""
                dynamic_node = list(dynamics)[0]
                value = dynamic_node.tag if dynamic_node.tag != "other-dynamics" else str(dynamic_node.text or "").strip()
                marks.append(
                    {
                        "event_id": event_id,
                        "measure": measure_number,
                        "staff": int(note.findtext("./staff") or 1),
                        "voice": local_voice_from_musicxml(int(note.findtext("./voice") or 1)),
                        "value": value,
                    }
                )
    return marks


def _host_notation_guidance(
    source: dict[str, Any],
    expected: dict[str, Any],
    diff: dict[str, Any],
) -> dict[str, Any] | None:
    """Explain event-level versus host-visible dynamics without hiding either."""

    changed_dynamic_ids = {
        str(item.get("event_id") or "")
        for item in diff.get("changed", [])
        if "dynamic" in (item.get("changed_fields") or [])
    }
    if not changed_dynamic_ids:
        return None

    source_marks = _exported_dynamic_marks(source)
    expected_marks = _exported_dynamic_marks(expected)
    source_keys = Counter((item["event_id"], item["value"]) for item in source_marks)
    expected_keys = Counter((item["event_id"], item["value"]) for item in expected_marks)

    added: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for mark in expected_marks:
        key = (mark["event_id"], mark["value"])
        if source_keys[key] > 0:
            source_keys[key] -= 1
        else:
            added.append(mark)
    for mark in source_marks:
        key = (mark["event_id"], mark["value"])
        if expected_keys[key] > 0:
            expected_keys[key] -= 1
        else:
            removed.append(mark)

    source_events = {
        str(event.get("event_id") or ""): event
        for measure in source.get("measures", [])
        for event in measure.get("events", [])
    }
    restoration_marks = [
        mark
        for mark in added
        if mark["event_id"] not in changed_dynamic_ids
        and str((source_events.get(mark["event_id"]) or {}).get("dynamic") or "").lower() == mark["value"]
    ]
    if restoration_marks:
        target_marks = [mark for mark in added if mark["event_id"] in changed_dynamic_ids]
        target_text = "、".join(f"{mark['event_id']}={mark['value']}" for mark in target_marks)
        restore_text = "、".join(f"{mark['event_id']}={mark['value']}" for mark in restoration_marks)
        explanation_zh = (
            f"MusicXML 力度记号是持续状态。MuseScore 应在目标音显示 {target_text}，并在随后音符显示恢复记号 "
            f"{restore_text}；恢复记号只保证未选音继续保持原力度，不是额外的事件级修改。"
        )
        explanation_en = (
            "MusicXML dynamics are persistent. MuseScore should show the target dynamic and then a reset mark on the "
            "following event; the reset preserves that event's original effective dynamic and is not an additional "
            "ScoreDocument edit."
        )
        kind = "isolated_dynamic_with_restore"
    else:
        explanation_zh = "MuseScore 中可见的力度记号应与下列宿主记号差异一致。"
        explanation_en = "The visible MuseScore dynamics should match the host-notation differences listed below."
        kind = "dynamic_change"

    return {
        "kind": kind,
        "changed_event_ids": sorted(changed_dynamic_ids),
        "dynamic_marks_added": added,
        "dynamic_marks_removed": removed,
        "restoration_marks": restoration_marks,
        "explanation_zh": explanation_zh,
        "explanation_en": explanation_en,
    }


class BenchmarkReviewService:
    """Load the benchmark, append reviews, and derive evidence-based gates."""

    def __init__(
        self,
        benchmark_root: Path | None = None,
        storage_root: Path | None = None,
        *,
        split_name: str = "core",
    ) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.benchmark_root = (benchmark_root or project_root / "benchmark").resolve()
        self.storage_root = (storage_root or _review_storage_root()).resolve()
        self.split_name = split_name
        self.review_path = self.storage_root / "benchmark_reviews.v1.jsonl"
        self.workspace_root = self.storage_root / "workspace"
        self.export_root = self.storage_root / "exports"
        self._lock = threading.Lock()
        self._task_fingerprint_cache: dict[str, str] = {}

    def _split(self) -> dict[str, Any]:
        split_path = self.benchmark_root / "splits" / f"{self.split_name}.json"
        if not split_path.exists():
            raise FileNotFoundError(f"benchmark split missing: {split_path}")
        return _read_json(split_path)

    def task_ids(self) -> list[str]:
        return [str(task_id) for task_id in self._split().get("task_ids", [])]

    def _load_assets(self, task_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        if task_id not in set(self.task_ids()):
            raise KeyError(task_id)
        task = load_task(self.benchmark_root, task_id)
        source = _read_json(self.benchmark_root / "source_scores" / f"{task['score_id']}.score.json")
        gold_path = task.get("gold_patch_path")
        expected_path = task.get("expected_output_path")
        gold = _read_json(self.benchmark_root / str(gold_path)) if gold_path else {}
        expected = _read_json(self.benchmark_root / str(expected_path)) if expected_path else source
        return task, source, gold, expected

    def records(self) -> list[dict[str, Any]]:
        if not self.review_path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.review_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("schema_version") == REVIEW_SCHEMA_VERSION:
                records.append(payload)
        return records

    def _current_task_fingerprint(self, task_id: str) -> str:
        if task_id not in self._task_fingerprint_cache:
            self._task_fingerprint_cache[task_id] = _canonical_hash(*self._load_assets(task_id))
        return self._task_fingerprint_cache[task_id]

    def _latest_by_task_role(self, records: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
        fingerprints = {task_id: self._current_task_fingerprint(task_id) for task_id in self.task_ids()}
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for record in records:
            task_id = str(record.get("task_id"))
            if record.get("task_fingerprint") != fingerprints.get(task_id):
                continue
            latest[(task_id, str(record.get("reviewer_role")))] = record
        return latest

    def submit_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = str(payload.get("task_id") or "").strip()
        task, source, gold, expected = self._load_assets(task_id)
        reviewer_id = str(payload.get("reviewer_id") or "").strip()
        role = str(payload.get("reviewer_role") or "").strip()
        decision = str(payload.get("decision") or "").strip()
        dimensions = payload.get("dimensions") or {}
        issues = list(dict.fromkeys(str(item) for item in (payload.get("issue_codes") or [])))
        notes = str(payload.get("notes") or "").strip()
        if not reviewer_id or len(reviewer_id) > 80:
            raise ValueError("reviewer_id must contain 1 to 80 characters")
        if role not in REVIEW_ROLES:
            raise ValueError("reviewer_role must be primary or secondary")
        if decision not in REVIEW_DECISIONS:
            raise ValueError("decision must be compliant, needs_revision, or exclude")
        if set(dimensions) != DIMENSION_KEYS:
            raise ValueError(f"dimensions must contain exactly: {sorted(DIMENSION_KEYS)}")
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 5 for value in dimensions.values()):
            raise ValueError("dimension ratings must be integers from 1 to 5")
        unknown_issues = sorted(set(issues) - ISSUE_CODES)
        if unknown_issues:
            raise ValueError(f"unknown issue codes: {unknown_issues}")
        if decision != "compliant" and not issues:
            raise ValueError("non-compliant reviews require at least one issue code")
        if len(notes) > 4000:
            raise ValueError("notes may not exceed 4000 characters")
        record = {
            "schema_version": REVIEW_SCHEMA_VERSION,
            "review_id": str(uuid.uuid4()),
            "task_id": task_id,
            "reviewer_id": reviewer_id,
            "reviewer_role": role,
            "decision": decision,
            "dimensions": {key: int(dimensions[key]) for key in sorted(DIMENSION_KEYS)},
            "issue_codes": issues,
            "notes": notes,
            "reviewed_at": datetime.now(UTC).isoformat(),
            "task_fingerprint": _canonical_hash(task, source, gold, expected),
        }
        self.storage_root.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self.review_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return {"saved": True, "review": record, "summary": self.summary()}

    def _automatic_validation_index(self) -> dict[str, dict[str, Any]]:
        report_path = self.benchmark_root / "validation" / f"{self.split_name}_report.json"
        if not report_path.exists():
            return {}
        report = _read_json(report_path)
        return {str(item.get("task_id")): item for item in report.get("details", [])}

    def _runtime_acceptance_evidence(self) -> tuple[dict[str, Any], dict[str, dict[str, Any]], Path | None]:
        """Load the latest product replay without treating it as model evidence."""

        report_path = self.benchmark_root / "validation" / f"{self.split_name}_runtime_acceptance_latest.json"
        if not report_path.exists():
            return {}, {}, None
        summary = _read_json(report_path)
        experiment_id = str(summary.get("experiment_id") or "")
        project_candidate = self.benchmark_root.parent / "experiments" / experiment_id
        recorded_candidate = Path(str(summary.get("experiment_dir") or ""))
        publication_snapshot = self.benchmark_root.parent / "experiments" / "softwarex_runtime_acceptance_720_v4"
        # Human review is tied to the curated, hashed publication snapshot.
        # Development replays may update the mutable latest pointer, but must
        # not silently replace the six-run bilingual evidence reviewers see.
        if publication_snapshot.is_dir():
            experiment_dir = publication_snapshot
        elif project_candidate.is_dir():
            experiment_dir = project_candidate
        else:
            experiment_dir = recorded_candidate
        experiment_summary_path = experiment_dir / "summary.json"
        if experiment_summary_path.is_file():
            # A frozen package may carry a mutable development "latest" pointer
            # alongside one curated publication snapshot. Once fallback selects
            # that snapshot, its own summary must remain paired with its metrics;
            # mixing a newer 120-run smoke summary with the frozen 720-run metrics
            # makes the review UI and packaged smoke report contradictory evidence.
            summary = _read_json(experiment_summary_path)
        metrics_path = experiment_dir / "metrics.csv"
        if not metrics_path.is_file():
            return summary, {}, None
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        with metrics_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                grouped[str(row.get("task_id") or "")].append(row)
        index: dict[str, dict[str, Any]] = {}
        for task_id, rows in grouped.items():
            passed = sum(str(row.get("task_success")) == "1" for row in rows)
            languages = sorted({str(row.get("language") or "en") for row in rows})
            index[task_id] = {
                "status": "passed" if passed == len(rows) else "failed",
                "runs": len(rows),
                "passed": passed,
                "failed": len(rows) - passed,
                "languages": languages,
                "repetitions": max((int(row.get("repetition") or 1) for row in rows), default=0),
                "generation_statuses": dict(Counter(str(row.get("generation_status") or "unknown") for row in rows)),
                "paper_model_result_eligible": False,
                "evidence_class": summary.get("evidence_class"),
            }
        return summary, index, experiment_dir

    def list_tasks(
        self,
        *,
        category: str = "",
        status: str = "",
        runtime_status: str = "",
        search: str = "",
    ) -> dict[str, Any]:
        latest = self._latest_by_task_role(self.records())
        automatic = self._automatic_validation_index()
        _runtime_summary, runtime, _experiment_dir = self._runtime_acceptance_evidence()
        normalized_search = search.casefold().strip()
        items: list[dict[str, Any]] = []
        for task_id in self.task_ids():
            task = load_task(self.benchmark_root, task_id)
            primary = latest.get((task_id, "primary"))
            secondary = latest.get((task_id, "secondary"))
            review_status = str(primary.get("decision")) if primary else "pending"
            runtime_evidence = runtime.get(task_id) or {"status": "unverified", "runs": 0, "passed": 0, "failed": 0, "languages": []}
            instruction = _display_instruction(task)
            if category and task.get("category") != category:
                continue
            if status and review_status != status:
                continue
            if runtime_status and runtime_evidence.get("status") != runtime_status:
                continue
            haystack = " ".join((task_id, instruction["en"], instruction["zh"], str(task.get("category", "")))).casefold()
            if normalized_search and normalized_search not in haystack:
                continue
            items.append(
                {
                    "task_id": task_id,
                    "score_id": task.get("score_id"),
                    "category": task.get("category"),
                    "difficulty": task.get("difficulty"),
                    "instruction": instruction,
                    "expected_status": task.get("expected_status"),
                    "review_status": review_status,
                    "primary_review": primary,
                    "secondary_review": secondary,
                    "automatic_valid": (automatic.get(task_id) or {}).get("valid"),
                    "runtime_acceptance": runtime_evidence,
                }
            )
        runtime_rank = {"failed": 0, "unverified": 1, "passed": 2}
        items.sort(
            key=lambda item: (
                runtime_rank.get(str((item.get("runtime_acceptance") or {}).get("status")), 1),
                0 if item.get("review_status") == "pending" else 1,
                str(item.get("task_id")),
            )
        )
        categories = sorted({str(load_task(self.benchmark_root, task_id).get("category", "")) for task_id in self.task_ids()})
        return {"split_id": self.split_name, "items": items, "categories": categories, "summary": self.summary()}

    def task_detail(self, task_id: str) -> dict[str, Any]:
        task, source, gold, expected = self._load_assets(task_id)
        diff = score_diff(source, expected)
        host_notation_guidance = _host_notation_guidance(source, expected, diff)
        latest = self._latest_by_task_role(self.records())
        _runtime_summary, runtime, experiment_dir = self._runtime_acceptance_evidence()
        runtime_evidence = dict(runtime.get(task_id) or {"status": "unverified", "runs": 0, "passed": 0, "failed": 0, "languages": []})
        runtime_evidence["host_outputs"] = {
            language: bool(self._runtime_output_path(experiment_dir, task_id, language))
            for language in runtime_evidence.get("languages", [])
        }
        source_event_count = sum(len(measure.get("events", [])) for measure in source.get("measures", []))
        expected_event_count = sum(len(measure.get("events", [])) for measure in expected.get("measures", []))
        return {
            "task": task | {"instruction": _display_instruction(task)},
            "score_summary": {
                "title": source.get("title"),
                "composer": source.get("composer"),
                "score_id": source.get("score_id"),
                "measure_count": len(source.get("measures", [])),
                "event_count": source_event_count,
                "key": (source.get("global") or {}).get("key"),
                "meter": (source.get("global") or {}).get("meter"),
                "parts": [part.get("name") or part.get("part_id") for part in source.get("parts", [])],
            },
            "expected_score_summary": {
                "measure_count": len(expected.get("measures", [])),
                "event_count": expected_event_count,
                "key": (expected.get("global") or {}).get("key"),
                "meter": (expected.get("global") or {}).get("meter"),
            },
            "gold_patch": gold,
            "diff": diff,
            "diff_rows": _diff_rows(diff),
            "host_notation_guidance": host_notation_guidance,
            "automatic_validation": self._automatic_validation_index().get(task_id),
            "runtime_acceptance": runtime_evidence,
            "primary_review": latest.get((task_id, "primary")),
            "secondary_review": latest.get((task_id, "secondary")),
            "task_fingerprint": _canonical_hash(task, source, gold, expected),
        }

    def summary(self) -> dict[str, Any]:
        task_ids = self.task_ids()
        records = self.records()
        latest = self._latest_by_task_role(records)
        current_fingerprints = {task_id: self._current_task_fingerprint(task_id) for task_id in task_ids}
        stale_records = sum(
            record.get("task_fingerprint") != current_fingerprints.get(str(record.get("task_id")))
            for record in records
        )
        primary = [latest[(task_id, "primary")] for task_id in task_ids if (task_id, "primary") in latest]
        secondary = [latest[(task_id, "secondary")] for task_id in task_ids if (task_id, "secondary") in latest]
        decisions = Counter(record["decision"] for record in primary)
        issue_counts = Counter(issue for record in primary for issue in record.get("issue_codes", []))
        category_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "reviewed": 0, "noncompliant": 0})
        for task_id in task_ids:
            task = load_task(self.benchmark_root, task_id)
            bucket = category_stats[str(task.get("category", "unknown"))]
            bucket["total"] += 1
            record = latest.get((task_id, "primary"))
            if record:
                bucket["reviewed"] += 1
                if record["decision"] != "compliant":
                    bucket["noncompliant"] += 1
        for bucket in category_stats.values():
            bucket["noncompliance_rate"] = round(bucket["noncompliant"] / max(1, bucket["reviewed"]), 4)

        reviewed_count = len(primary)
        noncompliant_count = decisions["needs_revision"] + decisions["exclude"]
        noncompliance_rate = noncompliant_count / max(1, reviewed_count)
        musical_problem_records = [
            record
            for record in primary
            if "musically_implausible" in record.get("issue_codes", [])
            or int((record.get("dimensions") or {}).get("musical_validity", 5)) <= 2
        ]
        musical_problem_rate = len(musical_problem_records) / max(1, reviewed_count)
        minimum_reviewed = 20
        benchmark_repair_required = reviewed_count >= minimum_reviewed and noncompliance_rate >= 0.20
        aesthetic_calibration_required = reviewed_count >= minimum_reviewed and musical_problem_rate >= 0.20
        if reviewed_count < minimum_reviewed:
            gate_status = "not_enough_reviews"
        elif aesthetic_calibration_required:
            gate_status = "aesthetic_calibration_required"
        elif benchmark_repair_required:
            gate_status = "benchmark_repair_required"
        else:
            gate_status = "monitoring"
        runtime_summary, runtime_index, _experiment_dir = self._runtime_acceptance_evidence()
        return {
            "split_id": self.split_name,
            "total": len(task_ids),
            "primary_reviewed": reviewed_count,
            "secondary_reviewed": len(secondary),
            "secondary_target": max(1, round(len(task_ids) * 0.25)),
            "stale_records": stale_records,
            "remaining": len(task_ids) - reviewed_count,
            "completion_rate": round(reviewed_count / max(1, len(task_ids)), 4),
            "decisions": dict(decisions),
            "noncompliance_rate": round(noncompliance_rate, 4),
            "issue_counts": dict(issue_counts),
            "categories": dict(sorted(category_stats.items())),
            "runtime_acceptance": {
                "available": bool(runtime_index),
                "experiment_id": runtime_summary.get("experiment_id"),
                "evidence_class": runtime_summary.get("evidence_class"),
                "paper_model_result_eligible": False,
                "tasks_passed": sum(item.get("status") == "passed" for item in runtime_index.values()),
                "tasks_failed": sum(item.get("status") == "failed" for item in runtime_index.values()),
                "runs": (runtime_summary.get("results") or {}).get("tasks", 0),
                "reproducibility": (runtime_summary.get("results") or {}).get("reproducibility"),
            },
            "calibration_gate": {
                "status": gate_status,
                "minimum_reviewed": minimum_reviewed,
                "threshold": 0.20,
                "benchmark_repair_required": benchmark_repair_required,
                "aesthetic_calibration_required": aesthetic_calibration_required,
                "musical_problem_count": len(musical_problem_records),
                "musical_problem_rate": round(musical_problem_rate, 4),
                "method": "blind_pairwise_preference_calibration",
                "target_pairwise_reviews": 24,
                "dimensions": [
                    "melodic_coherence",
                    "harmonic_motion",
                    "voice_leading",
                    "rhythmic_vitality",
                    "texture_balance",
                    "style_fidelity",
                    "playability",
                    "overall_preference",
                ],
                "boundary": "Human preferences may calibrate candidate ranking; they do not become proof of universal musical quality.",
            },
        }

    @staticmethod
    def _runtime_output_path(experiment_dir: Path | None, task_id: str, language: str) -> Path | None:
        if experiment_dir is None:
            return None
        candidates = sorted((experiment_dir / "host_outputs").glob(f"{task_id}__{language}__r*.musicxml"))
        if not candidates:
            compact = experiment_dir / "review_host_outputs" / f"{task_id}__{language}.musicxml"
            if compact.is_file():
                return compact
            legacy = experiment_dir / "host_outputs" / f"{task_id}__{language}.musicxml"
            return legacy if legacy.is_file() else None
        return candidates[-1]

    def prepare_artifact(self, task_id: str, variant: str) -> dict[str, Any]:
        if variant not in {"source", "expected", "runtime_en", "runtime_zh"}:
            raise ValueError("variant must be source, expected, runtime_en, or runtime_zh")
        task, _source, _gold, expected = self._load_assets(task_id)
        target_dir = self.workspace_root / task_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{variant}.musicxml"
        if variant == "source":
            source_path = self.benchmark_root / "source_scores" / f"{task['score_id']}.musicxml"
            target.write_bytes(source_path.read_bytes())
        elif variant == "expected":
            target.write_text(score_document_to_musicxml(expected), encoding="utf-8")
        else:
            language = variant.removeprefix("runtime_")
            _summary, runtime, experiment_dir = self._runtime_acceptance_evidence()
            evidence = runtime.get(task_id) or {}
            if evidence.get("status") != "passed":
                raise ValueError(f"runtime acceptance is not passed for {task_id}")
            runtime_path = self._runtime_output_path(experiment_dir, task_id, language)
            if runtime_path is None:
                if task.get("expected_status") != "refuse":
                    raise ValueError(f"runtime {language} MusicXML is unavailable for {task_id}")
                runtime_path = self.benchmark_root / "source_scores" / f"{task['score_id']}.musicxml"
            target.write_bytes(runtime_path.read_bytes())
        return {"task_id": task_id, "variant": variant, "path": str(target), "prepared": True}

    def export_reviews(self) -> dict[str, Any]:
        self.export_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        records = self.records()
        payload = {
            "schema_version": REVIEW_SCHEMA_VERSION,
            "exported_at": datetime.now(UTC).isoformat(),
            "summary": self.summary(),
            "records": records,
        }
        json_path = self.export_root / f"benchmark_reviews_{stamp}.json"
        csv_path = self.export_root / f"benchmark_reviews_{stamp}.csv"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "task_id",
                    "reviewer_id",
                    "reviewer_role",
                    "decision",
                    *sorted(DIMENSION_KEYS),
                    "issue_codes",
                    "notes",
                    "reviewed_at",
                    "task_fingerprint",
                ]
            )
            for record in records:
                writer.writerow(
                    [
                        record.get("task_id"),
                        record.get("reviewer_id"),
                        record.get("reviewer_role"),
                        record.get("decision"),
                        *((record.get("dimensions") or {}).get(key) for key in sorted(DIMENSION_KEYS)),
                        ";".join(record.get("issue_codes", [])),
                        record.get("notes"),
                        record.get("reviewed_at"),
                        record.get("task_fingerprint"),
                    ]
                )
        return {"exported": True, "json_path": str(json_path), "csv_path": str(csv_path), "record_count": len(records)}


_DEFAULT_SERVICE: BenchmarkReviewService | None = None


def default_benchmark_review_service() -> BenchmarkReviewService:
    """Return one process-local service so append locking is shared by API calls."""

    global _DEFAULT_SERVICE
    if _DEFAULT_SERVICE is None:
        _DEFAULT_SERVICE = BenchmarkReviewService()
    return _DEFAULT_SERVICE

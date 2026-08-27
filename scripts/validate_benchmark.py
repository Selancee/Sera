"""Validate SeraEdit benchmark tasks, gold patches, constraints, and round trips."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.validation.musicxml_validator import MusicXMLValidator
from backend.services.score_document_service import musicxml_to_score_document
from evaluation.analysis.music_statistics import parse_pitch_name
from evaluation.benchmark_io import load_task, resolve_task_path
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.execution.diff_engine import score_diff
from sera_edit.execution.transaction import PatchTransaction
from sera_edit.validation.schema_validator import validate_patch_schema


REQUIRED_TASK_FIELDS = {
    "task_id", "score_id", "category", "difficulty", "instruction_en", "instruction_zh",
    "target_scope", "protected_scope", "gold_patch_path", "expected_output_path",
    "expected_constraints", "expected_status", "unsupported_reason", "tags",
    "created_by", "review_status",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _event_index(score: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(event.get("event_id", "")): event
        for measure in score.get("measures") or []
        for event in measure.get("events") or []
    }


def _canonical_key(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-flat", "b")
        .replace(" flat", "b")
        .replace("-sharp", "#")
        .replace(" sharp", "#")
    )


def _normalized_values(value: object) -> list[str]:
    if isinstance(value, str):
        values = [value]
    else:
        values = list(value or [])
    return sorted(str(item).strip().lower().replace("_", "-") for item in values)


def evaluate_constraints(
    before: dict[str, Any],
    after: dict[str, Any],
    constraints: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    """Evaluate benchmark constraints without model-based judging."""

    errors: list[str] = []
    old = _event_index(before)
    new = _event_index(after)
    for constraint in constraints:
        kind = str(constraint.get("type", ""))
        if kind == "pitch_delta":
            delta = int(constraint["value"])
            for event_id in constraint.get("event_ids") or []:
                old_midi = parse_pitch_name(str(old[event_id].get("pitch", "")))
                new_midi = parse_pitch_name(str(new[event_id].get("pitch", "")))
                if old_midi is None or new_midi is None or new_midi - old_midi != delta:
                    errors.append(f"{event_id}: pitch delta is not {delta}")
        elif kind == "preserve_duration":
            offenders = [event_id for event_id in old.keys() & new.keys() if old[event_id].get("duration") != new[event_id].get("duration")]
            if offenders:
                errors.append(f"duration changed: {sorted(offenders)}")
        elif kind == "preserve_pitch":
            offenders = [event_id for event_id in old.keys() & new.keys() if old[event_id].get("pitch") != new[event_id].get("pitch")]
            if offenders:
                errors.append(f"pitch changed: {sorted(offenders)}")
        elif kind == "dynamic_equals":
            event_id = str(constraint["event_id"])
            if new.get(event_id, {}).get("dynamic") != constraint.get("value"):
                errors.append(f"{event_id}: dynamic mismatch")
        elif kind == "pitch_equals":
            event_id = str(constraint["event_id"])
            if new.get(event_id, {}).get("pitch") != constraint.get("value"):
                errors.append(f"{event_id}: pitch mismatch")
        elif kind == "duration_equals":
            event_id = str(constraint["event_id"])
            if new.get(event_id, {}).get("duration") != constraint.get("value"):
                errors.append(f"{event_id}: duration mismatch")
        elif kind == "articulation_equals":
            event_id = str(constraint["event_id"])
            if _normalized_values(new.get(event_id, {}).get("articulations")) != _normalized_values(constraint.get("value")):
                errors.append(f"{event_id}: articulation mismatch")
        elif kind in {"tie_equals", "slur_equals"}:
            event_id = str(constraint["event_id"])
            field = "tie" if kind == "tie_equals" else "slur"
            if (new.get(event_id, {}).get(field) or None) != (constraint.get("value") or None):
                errors.append(f"{event_id}: {field} mismatch")
        elif kind == "voice_equals":
            event_id = str(constraint["event_id"])
            if int(new.get(event_id, {}).get("voice", 0)) != int(constraint.get("value", 0)):
                errors.append(f"{event_id}: voice mismatch")
        elif kind == "grace_equals":
            event_id = str(constraint["event_id"])
            if bool(new.get(event_id, {}).get("grace")) != bool(constraint.get("value")):
                errors.append(f"{event_id}: grace mismatch")
        elif kind == "event_deleted":
            if str(constraint["event_id"]) in new:
                errors.append(f"{constraint['event_id']}: event was not deleted")
        elif kind == "event_inserted":
            event = new.get(str(constraint["event_id"]))
            if event is None:
                # Stable event IDs are required inside one product lineage, but
                # equivalent patches from independent generators need not copy
                # the Gold patch's invented insertion ID. Accept one unambiguous
                # newly added event with the requested semantic properties.
                candidates = [new[event_id] for event_id in sorted(new.keys() - old.keys())]
                if constraint.get("pitch") is not None:
                    candidates = [event for event in candidates if event.get("pitch") == constraint.get("pitch")]
                event = candidates[0] if len(candidates) == 1 else None
            if event is None:
                errors.append(f"{constraint['event_id']}: event was not inserted")
            elif constraint.get("pitch") is not None and event.get("pitch") != constraint.get("pitch"):
                errors.append(f"{constraint['event_id']}: inserted pitch mismatch")
        elif kind == "key_equals":
            if _canonical_key((after.get("global") or {}).get("key")) != _canonical_key(constraint.get("value")):
                errors.append("key signature mismatch")
        elif kind == "meter_equals":
            if str((after.get("global") or {}).get("meter")) != str(constraint.get("value")):
                errors.append("time signature mismatch")
        elif kind == "chord_pitches":
            requested_ids = [str(event_id) for event_id in constraint.get("event_ids") or []]
            if requested_ids and all(event_id in new for event_id in requested_ids):
                chord_events = [new[event_id] for event_id in requested_ids]
            else:
                # See event_inserted above: compare the inserted chord's notes,
                # not a generator-specific set of newly minted IDs.
                chord_events = [
                    new[event_id]
                    for event_id in sorted(new.keys() - old.keys())
                    if new[event_id].get("type") == "note"
                ]
            actual = sorted(str(event.get("pitch", "")) for event in chord_events)
            expected = sorted(str(value) for value in constraint.get("value") or [])
            if actual != expected:
                errors.append(f"chord pitches mismatch: {actual} != {expected}")
        elif kind == "changed_element_count":
            actual = int(score_diff(before, after).get("changed_element_count", 0))
            if actual != int(constraint.get("value", -1)):
                errors.append(f"changed element count is {actual}, not {constraint.get('value')}")
        elif kind == "refuse":
            continue
        else:
            errors.append(f"unsupported deterministic constraint: {kind}")
    return not errors, errors


def validate_split(benchmark_root: Path, split_name: str) -> dict[str, Any]:
    """Validate one split and return a serializable evidence report."""

    split = _load(benchmark_root / "splits" / f"{split_name}.json")
    details: list[dict[str, Any]] = []
    validator = MusicXMLValidator()
    for task_id in split["task_ids"]:
        errors: list[str] = []
        try:
            task_path = resolve_task_path(benchmark_root, task_id, split_name)
        except (FileNotFoundError, ValueError) as exc:
            details.append({"task_id": task_id, "valid": False, "errors": ["task file missing"]})
            continue
        task = load_task(benchmark_root, task_id, split_name)
        missing = sorted(REQUIRED_TASK_FIELDS - set(task))
        if missing:
            errors.append(f"missing task fields: {missing}")
        if task.get("task_id") != task_id:
            errors.append("task_id does not match filename/split")
        score_path = benchmark_root / "source_scores" / f"{task['score_id']}.score.json"
        musicxml_path = benchmark_root / "source_scores" / f"{task['score_id']}.musicxml"
        if not score_path.exists() or not musicxml_path.exists():
            errors.append("source score JSON or MusicXML missing")
            details.append({"task_id": task_id, "valid": False, "errors": errors})
            continue
        score = _load(score_path)
        source_validation = validator.validate_text(musicxml_path.read_text(encoding="utf-8"))
        if not source_validation.valid:
            errors.append(f"source MusicXML invalid: {source_validation.issues}")
        else:
            imported_source = musicxml_to_score_document(musicxml_path.read_text(encoding="utf-8"), source="benchmark_validation")
            if score_diff(score, imported_source).get("changed_element_count", 0):
                errors.append("source MusicXML does not reproduce the canonical source score")
        if task.get("expected_status") == "refuse":
            if task.get("gold_patch_path") is not None or not task.get("unsupported_reason"):
                errors.append("refusal task must have no gold patch and a reason")
            details.append(
                {
                    "task_id": task_id,
                    "valid": not errors,
                    "expected_status": "refuse",
                    "review_status": task.get("review_status"),
                    "errors": errors,
                }
            )
            continue
        gold_path = benchmark_root / str(task.get("gold_patch_path"))
        expected_path = benchmark_root / str(task.get("expected_output_path"))
        if not gold_path.exists() or not expected_path.exists():
            errors.append("gold patch or expected output missing")
            details.append({"task_id": task_id, "valid": False, "errors": errors})
            continue
        patch = _load(gold_path)
        schema_report = validate_patch_schema(patch)
        if schema_report.errors:
            errors.append(f"gold patch schema invalid: {schema_report.as_dict()}")
        result = PatchTransaction().execute(score, patch)
        if not result.committed:
            errors.append(f"gold patch did not commit: {result.report.as_dict()}")
        else:
            expected = _load(expected_path)
            if score_fingerprint(result.score_document) != score_fingerprint(expected):
                errors.append("expected output fingerprint mismatch")
            constraints_valid, constraint_errors = evaluate_constraints(score, result.score_document, task["expected_constraints"])
            if not constraints_valid:
                errors.extend(constraint_errors)
            if not result.report.checks.get("musicxml_roundtrip", {}).get("validator_valid"):
                errors.append("gold output failed MusicXML round-trip validation")
            expected_musicxml_path = expected_path.parent / expected_path.name.removesuffix(".score.json")
            expected_musicxml_path = expected_musicxml_path.with_suffix(".musicxml")
            if not expected_musicxml_path.exists():
                errors.append("expected MusicXML missing")
            else:
                expected_musicxml = expected_musicxml_path.read_text(encoding="utf-8")
                expected_musicxml_validation = validator.validate_text(expected_musicxml)
                if not expected_musicxml_validation.valid:
                    errors.append(f"expected MusicXML invalid: {expected_musicxml_validation.issues}")
                else:
                    imported_expected = musicxml_to_score_document(expected_musicxml, source="benchmark_validation")
                    if score_diff(expected, imported_expected).get("changed_element_count", 0):
                        errors.append("expected MusicXML does not reproduce the canonical expected score")
                    host_constraints_valid, host_constraint_errors = evaluate_constraints(
                        score,
                        imported_expected,
                        task["expected_constraints"],
                    )
                    if not host_constraints_valid:
                        errors.extend(f"expected MusicXML: {message}" for message in host_constraint_errors)
        details.append(
            {
                "task_id": task_id,
                "valid": not errors,
                "expected_status": "success",
                "review_status": task.get("review_status"),
                "errors": errors,
            }
        )
    valid_count = sum(1 for item in details if item["valid"])
    pending_review = sum(1 for item in details if item.get("review_status") == "pending_human_review")
    return {
        "split_id": split_name,
        "task_count": len(details),
        "valid_count": valid_count,
        "invalid_count": len(details) - valid_count,
        "automatic_validation_passed": valid_count == len(details),
        "human_review_pending": pending_review,
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, default=ROOT / "benchmark", help="Benchmark root directory")
    parser.add_argument("--split", default="batch1", help="Split filename without .json")
    parser.add_argument("--write-report", action="store_true", help="Write benchmark/validation/<split>_report.json")
    args = parser.parse_args()
    report = validate_split(args.benchmark_root.resolve(), args.split)
    if args.write_report:
        path = args.benchmark_root.resolve() / "validation" / f"{args.split}_report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "details"}, ensure_ascii=False, indent=2))
    if report["invalid_count"]:
        for item in report["details"]:
            if not item["valid"]:
                print(json.dumps(item, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate the deterministic 30-task SeraEdit Batch 1 benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.score_document_service import new_score_document, normalize_score_document, score_document_to_musicxml
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.execution.transaction import PatchTransaction


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _source_score(number: int) -> dict[str, Any]:
    keys = ["C major", "A minor", "G major", "D minor", "F major"]
    right = [
        ["C4", "D4", "E4", "G4"],
        ["A4", "C5", "E5", "D5"],
        ["G4", "A4", "B4", "D5"],
        ["D4", "F4", "A4", "G4"],
        ["F4", "A4", "C5", "B4"],
    ][number - 1]
    left = ["C3", "G2", "A2", "F2"]
    score = new_score_document(title=f"SeraEdit Synthetic Fixture {number}", key=keys[number - 1], measures=2)
    score["score_id"] = f"score_{number:03d}"
    score["metadata"].update(
        {
            "source": "seraedit_synthetic_public_domain",
            "license": "CC0-1.0",
            "benchmark_batch": "batch1",
        }
    )
    for measure_number, measure in enumerate(score["measures"], start=1):
        for staff, pitches in (("right_hand", right), ("left_hand", left)):
            label = "rh" if staff == "right_hand" else "lh"
            for index, pitch in enumerate(pitches, start=1):
                measure["events"].append(
                    {
                        "event_id": f"m{measure_number}_{label}_{index}",
                        "type": "note",
                        "pitch": pitch,
                        "duration": "quarter",
                        "offset": float(index - 1),
                        "voice": 1,
                        "staff": staff,
                        "tie": None,
                        "slur": None,
                        "accidental": "",
                        "dynamic": "mf",
                        "articulations": [],
                        "selected": False,
                    }
                )
    return normalize_score_document(score)


def _patch(
    score: dict[str, Any],
    task_id: str,
    instruction: str,
    target_scope: dict[str, Any],
    protected_scope: dict[str, Any],
    operations: list[dict[str, Any]],
    expected_effects: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "patch_id": f"gold_{task_id}",
        "source_score_id": score["score_id"],
        "source_fingerprint": score_fingerprint(score),
        "instruction": instruction,
        "target_scope": target_scope,
        "protected_scope": protected_scope,
        "preconditions": [],
        "operations": operations,
        "expected_effects": expected_effects,
        "provenance": {"provider": "rule_template", "model": "deterministic_batch1", "temperature": 0, "seed": 42},
    }


def _task_templates(score: dict[str, Any], sequence_start: int) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    source_number = int(score["score_id"].split("_")[-1])
    ids = {
        "pitch": f"pitch_{sequence_start:03d}",
        "rhythm": f"rhythm_{sequence_start:03d}",
        "dynamic": f"dynamics_{sequence_start:03d}",
        "insert": f"insertion_{sequence_start:03d}",
        "key": f"key_{sequence_start:03d}",
        "conflict": f"conflict_{sequence_start:03d}",
    }
    protected_left = {"staffs": [2]}
    results: list[tuple[dict[str, Any], dict[str, Any] | None]] = []

    target = {"measures": [1], "staffs": [1]}
    task_id = ids["pitch"]
    instruction_en = "Transpose measure 1 of staff 1 up by a major second while preserving rhythm."
    operations = [{"operation_id": f"{task_id}_op1", "type": "transpose", "selector": {"event_ids": [f"m1_rh_{i}" for i in range(1, 5)]}, "arguments": {"semitones": 2}, "preconditions": [], "expected_change_count": 4}]
    patch = _patch(score, task_id, instruction_en, target, protected_left, operations, [{"type": "preserve_duration"}])
    results.append((_task(task_id, score, "pitch_transposition", "easy", instruction_en, "将第1小节第一谱表升高大二度，并保持节奏不变。", target, protected_left, [{"type": "pitch_delta", "event_ids": [f"m1_rh_{i}" for i in range(1, 5)], "value": 2}, {"type": "preserve_duration"}]), patch))

    task_id = ids["rhythm"]
    target = {"measures": [2], "staffs": [1]}
    instruction_en = "Merge the first two quarter-note positions in measure 2 of staff 1 into one half note, preserving remaining pitches."
    operations = [
        {"operation_id": f"{task_id}_op1", "type": "set_duration", "selector": {"event_ids": ["m2_rh_1"]}, "arguments": {"duration": "half"}, "preconditions": [], "expected_change_count": 1},
        {"operation_id": f"{task_id}_op2", "type": "delete_event", "selector": {"event_ids": ["m2_rh_2"]}, "arguments": {}, "preconditions": [], "expected_change_count": 1}
    ]
    patch = _patch(score, task_id, instruction_en, target, protected_left, operations, [{"type": "changed_element_count", "value": 2}])
    results.append((_task(task_id, score, "rhythm_duration", "medium", instruction_en, "将第2小节第一谱表开头两个四分音符位置合并为一个二分音符，并保留其余音高。", target, protected_left, [{"type": "duration_equals", "event_id": "m2_rh_1", "value": "half"}, {"type": "event_deleted", "event_id": "m2_rh_2"}]), patch))

    task_id = ids["dynamic"]
    target = {"measures": [1], "staffs": [1], "event_ids": ["m1_rh_3"]}
    instruction_en = "Change only the third note in measure 1 to forte, preserving pitch and duration."
    operations = [{"operation_id": f"{task_id}_op1", "type": "set_dynamic", "selector": {"event_ids": ["m1_rh_3"]}, "arguments": {"dynamic": "f"}, "preconditions": [], "expected_change_count": 1}]
    patch = _patch(score, task_id, instruction_en, target, protected_left, operations, [{"type": "preserve_pitch"}, {"type": "preserve_duration"}])
    results.append((_task(task_id, score, "dynamics_articulation", "easy", instruction_en, "只将第1小节第三个音改为强奏，并保持音高与时值。", target, protected_left, [{"type": "dynamic_equals", "event_id": "m1_rh_3", "value": "f"}, {"type": "preserve_pitch"}, {"type": "preserve_duration"}]), patch))

    task_id = ids["insert"]
    target = {"measures": [2], "staffs": [1]}
    instruction_en = "Replace the final note of measure 2 staff 1 with F-sharp 4 without changing the measure duration."
    operations = [
        {"operation_id": f"{task_id}_op1", "type": "delete_event", "selector": {"event_ids": ["m2_rh_4"]}, "arguments": {}, "preconditions": [], "expected_change_count": 1},
        {"operation_id": f"{task_id}_op2", "type": "insert_note", "selector": {"measure": 2}, "arguments": {"event_id": f"{task_id}_replacement", "pitch": "F#4", "duration": "quarter", "offset": 3, "voice": 1, "staff": "right_hand"}, "preconditions": [], "expected_change_count": 1}
    ]
    patch = _patch(score, task_id, instruction_en, target, protected_left, operations, [{"type": "changed_element_count", "value": 2}])
    results.append((_task(task_id, score, "insertion_deletion", "medium", instruction_en, "将第2小节第一谱表最后一个音替换为升F4，并保持小节总时值。", target, protected_left, [{"type": "event_deleted", "event_id": "m2_rh_4"}, {"type": "event_inserted", "event_id": f"{task_id}_replacement", "pitch": "F#4"}]), patch))

    task_id = ids["key"]
    target = {"whole_score": True}
    new_key = ["G major", "C major", "D major", "A minor", "B-flat major"][source_number - 1]
    instruction_en = f"Change the score key signature to {new_key} without transposing notes."
    operations = [{"operation_id": f"{task_id}_op1", "type": "change_key_signature", "selector": {}, "arguments": {"key": new_key}, "preconditions": [], "expected_change_count": None}]
    patch = _patch(score, task_id, instruction_en, target, {}, operations, [{"type": "key_equals", "value": new_key}, {"type": "preserve_pitch"}])
    results.append((_task(task_id, score, "key_harmony", "easy", instruction_en, f"将调号改为{new_key}，但不要移调音符。", target, {}, [{"type": "key_equals", "value": new_key}, {"type": "preserve_pitch"}]), patch))

    task_id = ids["conflict"]
    target = {"measures": [1], "staffs": [1]}
    instruction_en = "Change measure 1 to 5/8 while preserving every note duration and leaving no rests."
    task = _task(task_id, score, "conflicting_or_unsupported", "hard", instruction_en, "把第1小节改成5/8拍，同时保持所有音符时值且不允许休止符。", target, protected_left, [{"type": "refuse", "reason": "meter_duration_conflict"}], expected_status="refuse", unsupported_reason="meter_duration_conflict")
    results.append((task, None))
    return results


def _task(
    task_id: str,
    score: dict[str, Any],
    category: str,
    difficulty: str,
    instruction_en: str,
    instruction_zh: str,
    target_scope: dict[str, Any],
    protected_scope: dict[str, Any],
    constraints: list[dict[str, Any]],
    *,
    expected_status: str = "success",
    unsupported_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "score_id": score["score_id"],
        "category": category,
        "difficulty": difficulty,
        "instruction_en": instruction_en,
        "instruction_zh": instruction_zh,
        "target_scope": target_scope,
        "protected_scope": protected_scope,
        "gold_patch_path": None if expected_status == "refuse" else f"gold_patches/{task_id}.json",
        "expected_output_path": None if expected_status == "refuse" else f"expected_outputs/{task_id}.score.json",
        "expected_constraints": constraints,
        "expected_status": expected_status,
        "unsupported_reason": unsupported_reason,
        "tags": ["batch1", "synthetic", "deterministic"],
        "created_by": "rule_template",
        "review_status": "pending_human_review",
    }


def generate(output_root: Path, *, force: bool = False) -> dict[str, Any]:
    """Generate all Batch 1 assets and fail rather than overwrite by default."""

    task_dir = output_root / "tasks" / "batch1"
    existing = list(task_dir.glob("*.json")) if task_dir.exists() else []
    if existing and not force:
        raise FileExistsError("Batch 1 files already exist; pass --force for deterministic regeneration")
    task_ids: list[str] = []
    category_counts: dict[str, int] = {}
    for source_number in range(1, 6):
        score = _source_score(source_number)
        _write_json(output_root / "source_scores" / f"score_{source_number:03d}.score.json", score)
        musicxml_path = output_root / "source_scores" / f"score_{source_number:03d}.musicxml"
        musicxml_path.parent.mkdir(parents=True, exist_ok=True)
        musicxml_path.write_text(score_document_to_musicxml(score), encoding="utf-8")
        for task, patch in _task_templates(score, source_number):
            task_id = task["task_id"]
            task_ids.append(task_id)
            category_counts[task["category"]] = category_counts.get(task["category"], 0) + 1
            _write_json(task_dir / f"{task_id}.json", task)
            if patch is not None:
                _write_json(output_root / "gold_patches" / f"{task_id}.json", patch)
                result = PatchTransaction().execute(score, patch)
                if not result.committed:
                    raise RuntimeError(f"gold patch {task_id} failed: {result.report.as_dict()}")
                _write_json(output_root / "expected_outputs" / f"{task_id}.score.json", result.score_document)
                (output_root / "expected_outputs" / f"{task_id}.musicxml").write_text(result.musicxml or "", encoding="utf-8")
                _write_json(output_root / "expected_outputs" / f"{task_id}.diff.json", result.diff)
    split = {"split_id": "batch1", "task_count": len(task_ids), "task_ids": sorted(task_ids), "category_counts": category_counts}
    _write_json(output_root / "splits" / "batch1.json", split)
    return split


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "benchmark", help="Benchmark root directory")
    parser.add_argument("--force", action="store_true", help="Regenerate existing deterministic Batch 1 files")
    args = parser.parse_args()
    summary = generate(args.output_root.resolve(), force=args.force)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

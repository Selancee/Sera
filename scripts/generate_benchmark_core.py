"""Generate deterministic SeraEdit Batch 2 (60 cumulative) and Core (120) assets."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.score_document_service import (
    musicxml_to_score_document,
    new_score_document,
    normalize_score_document,
    prepare_score_document_for_export,
    score_document_to_musicxml,
)
from backend.validation.musicxml_validator import MusicXMLValidator
from evaluation.benchmark_io import load_task
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.execution.transaction import PatchTransaction
from sera_edit.validation.duration_validator import validate_measure_durations
from sera_edit.validation.notation_relation_validator import validate_notation_relations
from sera_edit.validation.roundtrip_fidelity_validator import validate_roundtrip_fidelity


CATEGORY_PREFIX = {
    "pitch_transposition": "pitch",
    "rhythm_duration": "rhythm",
    "key_harmony": "key",
    "voice_texture": "voice",
    "dynamics_articulation": "dynamics",
    "insertion_deletion": "insertion",
    "ties_slurs_ornaments": "ties",
    "meter_measure_structure": "meter",
    "compound_multi_step": "compound",
    "conflicting_or_unsupported": "conflict",
}

BATCH2_ADDITIONS = {
    "pitch_transposition": 3,
    "rhythm_duration": 3,
    "key_harmony": 3,
    "voice_texture": 5,
    "dynamics_articulation": 2,
    "insertion_deletion": 2,
    "ties_slurs_ornaments": 4,
    "meter_measure_structure": 3,
    "compound_multi_step": 3,
    "conflicting_or_unsupported": 2,
}

BATCH3_ADDITIONS = {
    "pitch_transposition": 7,
    "rhythm_duration": 7,
    "key_harmony": 7,
    "voice_texture": 10,
    "dynamics_articulation": 3,
    "insertion_deletion": 3,
    "ties_slurs_ornaments": 6,
    "meter_measure_structure": 7,
    "compound_multi_step": 7,
    "conflicting_or_unsupported": 3,
}

INITIAL_SEQUENCE = {
    "pitch_transposition": 5,
    "rhythm_duration": 5,
    "key_harmony": 5,
    "voice_texture": 0,
    "dynamics_articulation": 5,
    "insertion_deletion": 5,
    "ties_slurs_ornaments": 0,
    "meter_measure_structure": 0,
    "compound_multi_step": 0,
    "conflicting_or_unsupported": 5,
}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _event(
    event_id: str,
    pitch: str,
    duration: str,
    offset: float,
    staff: str,
    *,
    voice: int = 1,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "type": "note",
        "pitch": pitch,
        "duration": duration,
        "offset": offset,
        "voice": voice,
        "staff": staff,
        "tie": None,
        "slur": None,
        "accidental": "",
        "dynamic": "mf",
        "articulations": [],
        "grace": False,
        "is_chord_tone": False,
        "chord_group_id": None,
        "selected": False,
    }


def _source_score(number: int) -> dict[str, Any]:
    """Create a three-measure public-domain synthetic fixture with varied notation."""

    keys = ["C major", "A minor", "G major", "D minor", "F major", "E minor", "B-flat major"]
    meter = "6/8" if number % 3 == 0 else "4/4"
    unit_duration = "eighth" if meter == "6/8" else "quarter"
    unit_count = 6 if meter == "6/8" else 4
    unit_size = 0.5 if meter == "6/8" else 1.0
    score = new_score_document(
        title=f"SeraEdit Synthetic Core Fixture {number}",
        composer="SeraEdit deterministic fixture generator",
        key=keys[(number - 1) % len(keys)],
        meter=meter,
        tempo=72 + (number % 5) * 6,
        measures=3,
    )
    score["score_id"] = f"score_{number:03d}"
    score["metadata"].update(
        {
            "source": "seraedit_synthetic_public_domain",
            "license": "CC0-1.0",
            "benchmark_batch": "batch2" if number <= 10 else "batch3",
            "feature_profile": [],
        }
    )
    right_scale = ["C4", "D4", "E4", "G4", "A4", "B4", "C5"]
    left_scale = ["C3", "G2", "A2", "F2", "E3", "D3", "G3"]
    for measure_number, measure in enumerate(score["measures"], start=1):
        for index in range(unit_count):
            right_pitch = right_scale[(number + measure_number + index) % len(right_scale)]
            left_pitch = left_scale[(number + measure_number * 2 + index) % len(left_scale)]
            measure["events"].append(
                _event(
                    f"s{number:03d}_m{measure_number}_rh_{index + 1}",
                    right_pitch,
                    unit_duration,
                    index * unit_size,
                    "right_hand",
                )
            )
            measure["events"].append(
                _event(
                    f"s{number:03d}_m{measure_number}_lh_{index + 1}",
                    left_pitch,
                    unit_duration,
                    index * unit_size,
                    "left_hand",
                )
            )

    if number % 2 == 0:
        voice_duration = "dotted_half" if meter == "6/8" else "whole"
        for measure_number, measure in enumerate(score["measures"], start=1):
            measure["events"].append(
                _event(
                    f"s{number:03d}_m{measure_number}_lh_v2_1",
                    left_scale[(number + measure_number) % len(left_scale)],
                    voice_duration,
                    0,
                    "left_hand",
                    voice=2,
                )
            )
        score["metadata"]["feature_profile"].append("independent_second_voice")

    if number % 3 == 1:
        measure = score["measures"][0]
        primary = next(event for event in measure["events"] if event["event_id"] == f"s{number:03d}_m1_lh_1")
        primary["chord_group_id"] = f"s{number:03d}_source_chord"
        chord_tone = json.loads(json.dumps(primary))
        chord_tone.update(
            {
                "event_id": f"s{number:03d}_m1_lh_chord_2",
                "pitch": "E3",
                "is_chord_tone": True,
            }
        )
        measure["events"].append(chord_tone)
        score["metadata"]["feature_profile"].append("chord")
    elif number % 3 == 2:
        score["measures"][0]["events"] = _set_relation(
            score["measures"][0]["events"],
            f"s{number:03d}_m1_rh_1",
            f"s{number:03d}_m1_rh_{unit_count}",
            "slur",
        )
        score["metadata"]["feature_profile"].append("slur")
    else:
        grace = _event(
            f"s{number:03d}_m1_rh_grace_1",
            "B3",
            "eighth",
            unit_size,
            "right_hand",
        )
        grace.update({"grace": True, "articulations": ["accent"]})
        score["measures"][0]["events"].append(grace)
        score["metadata"]["feature_profile"].append("grace_note")

    if number % 5 == 0:
        start_id = f"s{number:03d}_m1_lh_{unit_count}"
        stop_id = f"s{number:03d}_m2_lh_1"
        start = next(event for event in score["measures"][0]["events"] if event["event_id"] == start_id)
        stop = next(event for event in score["measures"][1]["events"] if event["event_id"] == stop_id)
        stop["pitch"] = start["pitch"]
        start["tie"] = "start"
        stop["tie"] = "stop"
        score["metadata"]["feature_profile"].append("cross_measure_tie")

    return prepare_score_document_for_export(score)


def _set_relation(events: list[dict[str, Any]], start_id: str, stop_id: str, field: str) -> list[dict[str, Any]]:
    for event in events:
        if event["event_id"] == start_id:
            event[field] = "start"
        elif event["event_id"] == stop_id:
            event[field] = "stop"
    return events


def _validate_source(score: dict[str, Any]) -> str:
    duration = validate_measure_durations(score)
    notation = validate_notation_relations(score)
    if duration.errors or notation.errors:
        raise RuntimeError(
            f"source {score['score_id']} failed canonical validation: "
            f"duration={duration.as_dict()} notation={notation.as_dict()}"
        )
    musicxml = score_document_to_musicxml(score)
    xml_validation = MusicXMLValidator().validate_text(musicxml)
    if not xml_validation.valid:
        raise RuntimeError(f"source {score['score_id']} MusicXML invalid: {xml_validation.issues}")
    imported = musicxml_to_score_document(musicxml, source="seraedit_core_source_roundtrip")
    fidelity = validate_roundtrip_fidelity(score, imported)
    if fidelity.errors:
        raise RuntimeError(f"source {score['score_id']} round-trip failed: {fidelity.as_dict()}")
    return musicxml


def _round_robin_schedule(counts: dict[str, int]) -> list[str]:
    remaining = dict(counts)
    schedule: list[str] = []
    while any(remaining.values()):
        for category in CATEGORY_PREFIX:
            if remaining.get(category, 0) > 0:
                schedule.append(category)
                remaining[category] -= 1
    return schedule


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
        "provenance": {
            "provider": "rule_template",
            "model": "deterministic_core_v1",
            "temperature": 0,
            "seed": 42,
        },
    }


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
    batch: str,
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
        "tags": [batch, "synthetic", "deterministic", category],
        "created_by": "rule_template",
        "review_status": "pending_human_review",
    }


def _op(operation_id: str, op_type: str, selector: dict[str, Any], arguments: dict[str, Any], count: int | None) -> dict[str, Any]:
    return {
        "operation_id": operation_id,
        "type": op_type,
        "selector": selector,
        "arguments": arguments,
        "preconditions": [],
        "expected_change_count": count,
    }


def _build_task(
    score: dict[str, Any],
    category: str,
    sequence: int,
    batch: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    number = int(score["score_id"].split("_")[-1])
    task_id = f"{CATEGORY_PREFIX[category]}_{sequence:03d}"
    meter = str(score["global"]["meter"])
    count = 6 if meter == "6/8" else 4
    unit = "eighth" if meter == "6/8" else "quarter"
    replacement_duration = "quarter" if meter == "6/8" else "half"
    protected_left = {"staffs": [2]}
    right = lambda measure, index: f"s{number:03d}_m{measure}_rh_{index}"  # noqa: E731

    if category == "pitch_transposition":
        ids = [right(1, index) for index in range(1, count + 1)]
        semitones = -2 if sequence % 2 == 0 else 2
        instruction = f"Transpose measure 1 of staff 1 by {semitones:+d} semitones while preserving rhythm."
        zh = f"将第1小节第一谱表移调{semitones:+d}个半音，并保持节奏不变。"
        target = {"measures": [1], "staffs": [1]}
        operations = [_op(f"{task_id}_op1", "transpose", {"event_ids": ids}, {"semitones": semitones}, len(ids))]
        constraints = [{"type": "pitch_delta", "event_ids": ids, "value": semitones}, {"type": "preserve_duration"}]
        effects = [{"type": "preserve_duration"}]
        difficulty = "easy"
    elif category == "rhythm_duration":
        first, second = right(2, 1), right(2, 2)
        instruction = "Merge the first two rhythmic units of measure 2 staff 1 while preserving the remaining events."
        zh = "合并第2小节第一谱表开头的两个节奏单位，并保留其余事件。"
        target = {"measures": [2], "staffs": [1]}
        operations = [
            _op(f"{task_id}_op1", "set_duration", {"event_ids": [first]}, {"duration": replacement_duration}, 1),
            _op(f"{task_id}_op2", "delete_event", {"event_ids": [second]}, {}, 1),
        ]
        constraints = [{"type": "duration_equals", "event_id": first, "value": replacement_duration}, {"type": "event_deleted", "event_id": second}]
        effects = []
        difficulty = "medium"
    elif category == "key_harmony":
        keys = ["D major", "E-flat major", "B minor", "G minor"]
        new_key = keys[sequence % len(keys)]
        if new_key == score["global"]["key"]:
            new_key = keys[(sequence + 1) % len(keys)]
        instruction = f"Change the key signature to {new_key} without transposing any note."
        zh = f"将调号改为{new_key}，但不要移调任何音符。"
        target = {"whole_score": True}
        protected_left = {}
        operations = [_op(f"{task_id}_op1", "change_key_signature", {}, {"key": new_key}, None)]
        constraints = [{"type": "key_equals", "value": new_key}, {"type": "preserve_pitch"}]
        effects = [{"type": "key_equals", "value": new_key}, {"type": "preserve_pitch"}]
        difficulty = "easy"
    elif category == "voice_texture":
        ids = [right(3, index) for index in range(1, count + 1)]
        instruction = "Move all notes in measure 3 staff 1 from voice 1 to voice 2, preserving pitch and rhythm."
        zh = "将第3小节第一谱表的全部音符从声部1移到声部2，并保持音高和节奏。"
        target = {"measures": [3], "staffs": [1]}
        operations = [_op(f"{task_id}_op1", "move_to_voice", {"event_ids": ids}, {"voice": 2}, len(ids))]
        constraints = [{"type": "voice_equals", "event_id": event_id, "value": 2} for event_id in ids]
        constraints.extend([{"type": "preserve_pitch"}, {"type": "preserve_duration"}])
        effects = [{"type": "preserve_pitch"}, {"type": "preserve_duration"}]
        difficulty = "medium"
    elif category == "dynamics_articulation":
        event_id = right(2, min(3, count))
        target = {"measures": [2], "staffs": [1], "event_ids": [event_id]}
        if sequence % 2:
            instruction = "Set only the selected note to forte while preserving pitch and duration."
            zh = "只将所选音符改为强奏，并保持音高和时值。"
            operations = [_op(f"{task_id}_op1", "set_dynamic", {"event_ids": [event_id]}, {"dynamic": "f"}, 1)]
            constraints = [{"type": "dynamic_equals", "event_id": event_id, "value": "f"}, {"type": "preserve_pitch"}, {"type": "preserve_duration"}]
        else:
            instruction = "Add staccato to only the selected note while preserving pitch and duration."
            zh = "只给所选音符添加断奏，并保持音高和时值。"
            operations = [_op(f"{task_id}_op1", "set_articulation", {"event_ids": [event_id]}, {"articulations": ["staccato"]}, 1)]
            constraints = [{"type": "articulation_equals", "event_id": event_id, "value": ["staccato"]}, {"type": "preserve_pitch"}, {"type": "preserve_duration"}]
        effects = [{"type": "preserve_pitch"}, {"type": "preserve_duration"}]
        difficulty = "easy"
    elif category == "insertion_deletion":
        event_id = right(2, 1)
        target = {"measures": [2], "staffs": [1]}
        if sequence % 2:
            replacement_id = f"{task_id}_replacement"
            instruction = "Replace the first note of measure 2 staff 1 with F-sharp 4 without changing its duration."
            zh = "将第2小节第一谱表的第一个音替换为升F4，并保持时值不变。"
            operations = [
                _op(f"{task_id}_op1", "delete_event", {"event_ids": [event_id]}, {}, 1),
                _op(
                    f"{task_id}_op2",
                    "insert_note",
                    {"measure": 2},
                    {"event_id": replacement_id, "pitch": "F#4", "duration": unit, "offset": 0, "voice": 1, "staff": "right_hand"},
                    1,
                ),
            ]
            constraints = [{"type": "event_deleted", "event_id": event_id}, {"type": "event_inserted", "event_id": replacement_id, "pitch": "F#4"}]
            effects = [{"type": "changed_element_count", "value": 2}]
        else:
            chord_ids = [f"{task_id}_op1_chord_{index}" for index in range(1, 4)]
            instruction = "Replace the first note of measure 2 staff 1 with a C-major triad of the same duration."
            zh = "将第2小节第一谱表的第一个音替换为同样时值的C大三和弦。"
            operations = [_op(f"{task_id}_op1", "replace_chord", {"event_ids": [event_id]}, {"pitches": ["C4", "E4", "G4"]}, 4)]
            constraints = [{"type": "event_deleted", "event_id": event_id}, {"type": "chord_pitches", "event_ids": chord_ids, "value": ["C4", "E4", "G4"]}]
            effects = []
        difficulty = "medium"
    elif category == "ties_slurs_ornaments":
        first, last = right(3, 1), right(3, count)
        instruction = "Add one slur from the first to the last note of measure 3 staff 1."
        zh = "在第3小节第一谱表的第一个音到最后一个音之间添加一条连音线。"
        target = {"measures": [3], "staffs": [1]}
        operations = [
            _op(f"{task_id}_op1", "set_slur", {"event_ids": [first]}, {"slur": "start"}, 1),
            _op(f"{task_id}_op2", "set_slur", {"event_ids": [last]}, {"slur": "stop"}, 1),
        ]
        constraints = [{"type": "slur_equals", "event_id": first, "value": "start"}, {"type": "slur_equals", "event_id": last, "value": "stop"}, {"type": "preserve_pitch"}, {"type": "preserve_duration"}]
        effects = [{"type": "preserve_pitch"}, {"type": "preserve_duration"}]
        difficulty = "medium"
    elif category == "meter_measure_structure" and sequence == 1 and meter == "4/4":
        new_meter = "3/4"
        deleted_ids = [
            f"s{number:03d}_m{measure}_{staff}_4"
            for measure in range(1, 4)
            for staff in ("rh", "lh")
        ]
        instruction = (
            "Rebar the three-measure excerpt from 4/4 to 3/4 by removing the final "
            "quarter-note event from each staff in every measure; preserve every remaining pitch and duration."
        )
        zh = "将这段三小节乐谱从4/4改为3/4：删除每个小节每个谱表最后一个四分音符，并保留其余音符的音高和时值。"
        target = {"whole_score": True}
        protected_left = {}
        operations = [
            _op(f"{task_id}_op1", "change_time_signature", {}, {"meter": new_meter}, None),
            _op(f"{task_id}_op2", "delete_event", {"event_ids": deleted_ids}, {}, len(deleted_ids)),
        ]
        constraints = [
            {"type": "meter_equals", "value": new_meter},
            *({"type": "event_deleted", "event_id": event_id} for event_id in deleted_ids),
            {"type": "preserve_duration"},
            {"type": "preserve_pitch"},
        ]
        effects = list(constraints)
        difficulty = "hard"
    elif category == "meter_measure_structure":
        new_meter = "3/4" if meter == "6/8" else "2/2"
        instruction = (
            f"Replace only the displayed global time signature from {meter} to {new_meter}; "
            "do not rebar, regroup, or change any event."
        )
        zh = f"仅将全谱显示拍号从{meter}替换为{new_meter}；不要重新划分小节、重组节拍或修改任何事件。"
        target = {"whole_score": True}
        protected_left = {}
        operations = [_op(f"{task_id}_op1", "change_time_signature", {}, {"meter": new_meter}, None)]
        constraints = [{"type": "meter_equals", "value": new_meter}, {"type": "preserve_duration"}, {"type": "preserve_pitch"}]
        effects = [{"type": "meter_equals", "value": new_meter}, {"type": "preserve_duration"}, {"type": "preserve_pitch"}]
        difficulty = "medium"
    elif category == "compound_multi_step":
        ids = [right(2, count - 1), right(2, count)]
        instruction = "Transpose the final two notes of measure 2 staff 1 up a semitone and mark the final note forte."
        zh = "将第2小节第一谱表最后两个音升高半音，并把最后一个音标为强奏。"
        target = {"measures": [2], "staffs": [1]}
        operations = [
            _op(f"{task_id}_op1", "transpose", {"event_ids": ids}, {"semitones": 1}, 2),
            _op(f"{task_id}_op2", "set_dynamic", {"event_ids": [ids[-1]]}, {"dynamic": "f"}, 1),
        ]
        constraints = [{"type": "pitch_delta", "event_ids": ids, "value": 1}, {"type": "dynamic_equals", "event_id": ids[-1], "value": "f"}, {"type": "preserve_duration"}]
        effects = [{"type": "preserve_duration"}]
        difficulty = "hard"
    else:
        target = {"measures": [1], "staffs": [1]}
        reason = "meter_duration_conflict" if sequence % 2 else "unsupported_ornament_semantics"
        if reason == "meter_duration_conflict":
            instruction = "Change measure 1 to 5/8 while preserving all durations and adding no rests."
            zh = "把第1小节改成5/8拍，同时保持全部时值且不添加休止符。"
        else:
            instruction = "Make the selected phrase sound mysteriously more beautiful without changing any notation."
            zh = "让所选乐句听起来更神秘、更优美，但不要改变任何记谱内容。"
        return (
            _task(
                task_id,
                score,
                category,
                "hard",
                instruction,
                zh,
                target,
                protected_left,
                [{"type": "refuse", "reason": reason}],
                batch,
                expected_status="refuse",
                unsupported_reason=reason,
            ),
            None,
        )

    task = _task(
        task_id,
        score,
        category,
        difficulty,
        instruction,
        zh,
        target,
        protected_left,
        constraints,
        batch,
    )
    return task, _patch(score, task_id, instruction, target, protected_left, operations, effects)


def _generate_batch(
    output_root: Path,
    batch: str,
    source_numbers: range,
    schedule: list[str],
    sequence: dict[str, int],
    *,
    force: bool,
) -> list[str]:
    task_dir = output_root / "tasks" / batch
    existing = sorted(task_dir.glob("*.json")) if task_dir.exists() else []
    if existing and len(existing) != len(schedule) and not force:
        raise FileExistsError(f"{batch} is partially generated ({len(existing)}/{len(schedule)}); pass --force")
    if existing and len(existing) == len(schedule) and not force:
        for category in schedule:
            sequence[category] += 1
        return [path.stem for path in existing]

    task_ids: list[str] = []
    schedule_index = 0
    for source_number in source_numbers:
        score = _source_score(source_number)
        musicxml = _validate_source(score)
        _write_json(output_root / "source_scores" / f"score_{source_number:03d}.score.json", score)
        musicxml_path = output_root / "source_scores" / f"score_{source_number:03d}.musicxml"
        musicxml_path.parent.mkdir(parents=True, exist_ok=True)
        musicxml_path.write_text(musicxml, encoding="utf-8")
        for _ in range(6):
            category = schedule[schedule_index]
            schedule_index += 1
            sequence[category] += 1
            task, patch = _build_task(score, category, sequence[category], batch)
            task_id = str(task["task_id"])
            task_ids.append(task_id)
            _write_json(task_dir / f"{task_id}.json", task)
            if patch is None:
                continue
            _write_json(output_root / "gold_patches" / f"{task_id}.json", patch)
            result = PatchTransaction().execute(score, patch)
            if not result.committed:
                raise RuntimeError(f"gold patch {task_id} failed: {result.report.as_dict()}")
            _write_json(output_root / "expected_outputs" / f"{task_id}.score.json", result.score_document)
            (output_root / "expected_outputs" / f"{task_id}.musicxml").write_text(result.musicxml or "", encoding="utf-8")
            _write_json(output_root / "expected_outputs" / f"{task_id}.diff.json", result.diff)
    return task_ids


def _split(output_root: Path, split_id: str, task_ids: list[str]) -> dict[str, Any]:
    categories = Counter(load_task(output_root, task_id).get("category") for task_id in task_ids)
    split = {
        "split_id": split_id,
        "task_count": len(task_ids),
        "task_ids": task_ids,
        "category_counts": dict(sorted(categories.items())),
        "review_status": "pending_human_review",
    }
    _write_json(output_root / "splits" / f"{split_id}.json", split)
    return split


def _write_review_checklist(output_root: Path, split: dict[str, Any]) -> None:
    path = output_root / "review" / f"{split['split_id']}_human_review.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["task_id", "score_id", "category", "instruction_en", "instruction_zh", "review_status", "reviewer_notes"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for task_id in split["task_ids"]:
            task = load_task(output_root, task_id)
            writer.writerow(
                {
                    "task_id": task_id,
                    "score_id": task["score_id"],
                    "category": task["category"],
                    "instruction_en": task["instruction_en"],
                    "instruction_zh": task["instruction_zh"],
                    "review_status": task["review_status"],
                    "reviewer_notes": "",
                }
            )


def _write_source_manifest(output_root: Path, source_count: int) -> None:
    sources = []
    for number in range(1, source_count + 1):
        score = json.loads((output_root / "source_scores" / f"score_{number:03d}.score.json").read_text(encoding="utf-8"))
        sources.append(
            {
                "score_id": score["score_id"],
                "title": score["title"],
                "meter": score["global"]["meter"],
                "key": score["global"]["key"],
                "measure_count": len(score["measures"]),
                "features": score.get("metadata", {}).get("feature_profile", ["two_staff_quarter_note_fixture"]),
                "source": score.get("metadata", {}).get("source"),
                "license": score.get("metadata", {}).get("license"),
            }
        )
    _write_json(output_root / "source_scores" / "manifest.json", {"source_count": len(sources), "sources": sources})


def generate(output_root: Path, target: int, *, force: bool = False) -> dict[str, Any]:
    """Generate a cumulative 60-task or 120-task benchmark."""

    if target not in {60, 120}:
        raise ValueError("target must be 60 or 120")
    batch1 = json.loads((output_root / "splits" / "batch1.json").read_text(encoding="utf-8"))
    if int(batch1.get("task_count", 0)) != 30:
        raise RuntimeError("validated Batch 1 with exactly 30 tasks is required")
    sequence = dict(INITIAL_SEQUENCE)
    batch2_ids = _generate_batch(
        output_root,
        "batch2",
        range(6, 11),
        _round_robin_schedule(BATCH2_ADDITIONS),
        sequence,
        force=force,
    )
    development_ids = [*batch1["task_ids"], *batch2_ids]
    development = _split(output_root, "batch2", development_ids)
    _write_review_checklist(output_root, development)
    result: dict[str, Any] = {"batch2": development}
    if target == 120:
        batch3_ids = _generate_batch(
            output_root,
            "batch3",
            range(11, 21),
            _round_robin_schedule(BATCH3_ADDITIONS),
            sequence,
            force=force,
        )
        _split(output_root, "batch3", batch3_ids)
        core = _split(output_root, "core", [*development_ids, *batch3_ids])
        _write_review_checklist(output_root, core)
        result["core"] = core
        _write_source_manifest(output_root, 20)
    else:
        _write_source_manifest(output_root, 10)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "benchmark", help="Benchmark root directory")
    parser.add_argument("--target", type=int, choices=(60, 120), default=60, help="Cumulative task count")
    parser.add_argument("--force", action="store_true", help="Regenerate only Batch 2/3 deterministic assets")
    args = parser.parse_args()
    summary = generate(args.output_root.resolve(), args.target, force=args.force)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

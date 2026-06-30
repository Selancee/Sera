"""Run the Sera V0.8 Workbench editing benchmark."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from backend.agents.score_editing_agent import ScoreEditingAgent
from backend.services.accompaniment_service import generate_left_hand_accompaniment_patch
from backend.services.project_migration_service import migrate_workbench_project
from backend.services.score_document_service import new_score_document, score_document_to_musicxml
from backend.services.score_operation_service import apply_score_operation, undo_last, redo_last
from backend.services.score_patch_service import ScorePatchService
from backend.validation.musicxml_validator import MusicXMLValidator
from evaluation.workbench_editing.workbench_edit_metrics import METRIC_COLUMNS, score_workbench_case, summarize_rows


ROOT = Path(__file__).resolve().parents[2]
PROMPTS = Path(__file__).with_name("workbench_edit_prompt_sets_v08.json")
RESULT_DIR = ROOT / "evaluation" / "results"


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    score = new_score_document(measures=8)
    history = {"done": [], "undone": []}
    selected_range = case.get("selected_range", {"start_measure": 1, "end_measure": 2})
    result: dict[str, Any] = {
        "case_id": case["id"],
        "type": case["type"],
        "prompt": case["prompt"],
        "selection_ok": True,
        "undo_redo_ok": True,
        "musicxml_valid": False,
    }

    if case["type"] == "note_input":
        score, op = apply_score_operation(score, {"source": "user", "type": "insert_note", "target": {"measure": 1}, "after": {"pitch": "C4", "duration": "quarter", "offset": 0}, "description": "note input"})
        history["done"].append(op)
        result["note_input_ok"] = len(score["measures"][0]["events"]) == 1
    elif case["type"] == "keyboard":
        score, op = apply_score_operation(score, {"source": "user", "type": "insert_note", "target": {"measure": 1}, "after": {"pitch": "D4", "duration": "quarter", "offset": 0}, "description": "keyboard input"})
        history["done"].append(op)
        result["keyboard_ok"] = score["measures"][0]["events"][0]["pitch"] == "D4"
    elif case["type"] == "drag":
        score, op = apply_score_operation(score, {"source": "user", "type": "insert_note", "target": {"measure": 1}, "after": {"event_id": "n1", "pitch": "C4", "duration": "quarter", "offset": 0}, "description": "seed"})
        history["done"].append(op)
        score, op = apply_score_operation(score, {"source": "user", "type": "update_pitch", "target": {"measure": 1, "event_id": "n1"}, "after": {"pitch": "D4"}, "description": "drag pitch"})
        history["done"].append(op)
        result["drag_ok"] = score["measures"][0]["events"][0]["pitch"] == "D4"
    elif case["type"] == "accompaniment":
        patch = generate_left_hand_accompaniment_patch(score, selected_range, case.get("texture", "arpeggiated"))
        preview = ScorePatchService().apply_patch(score, patch, "generate accompaniment", selected_range, {"preserve_harmony": True})
        score = preview["score_document"]
        result["accompaniment_ok"] = bool(preview.get("accepted")) and bool(patch["operations"])
    elif case["type"] == "agent":
        score["measures"][0]["events"].append({"event_id": "n1", "type": "note", "pitch": "C4", "duration": "quarter", "offset": 0, "voice": 1, "staff": "right_hand"})
        patch = ScoreEditingAgent().create_patch(
            score,
            case["prompt"],
            selected_range,
            {"preserve_manual_edits": True, **case.get("constraints", {})},
            edit_context={"recent_operations": [{"source": "user", "target": {"event_id": "n1"}}]},
        )
        result["agent_preserve_ok"] = any("n1" in operation.get("target", {}).get("exclude_event_ids", []) for operation in patch.get("operations", []))
    elif case["type"] == "autosave":
        project = {"score_document": score, "operation_history": history, "project_version": "0.8"}
        result["autosave_ok"] = json.loads(json.dumps(project))["project_version"] == "0.8"
    elif case["type"] == "project":
        migrated = migrate_workbench_project({"ScoreDocument": score, "OperationHistory": history})
        result["migration_ok"] = migrated["project_version"] == "0.8"

    if history["done"]:
        previous, undone = undo_last(score, history)
        redone, _ = redo_last(previous, undone)
        result["undo_redo_ok"] = bool(redone.get("measures"))
    musicxml = score_document_to_musicxml(score)
    result["musicxml_valid"] = bool(MusicXMLValidator().validate_text(musicxml).to_report().get("valid_musicxml"))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-prompts", type=int, default=0)
    parser.add_argument("--prompt-set", type=Path, default=PROMPTS)
    parser.add_argument("--output-dir", type=Path, default=RESULT_DIR)
    args = parser.parse_args()

    cases = json.loads(args.prompt_set.read_text(encoding="utf-8"))
    if args.max_prompts:
        cases = cases[: args.max_prompts]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for case in cases:
        result = run_case(case)
        metrics = score_workbench_case(case, result)
        row = {**result, **metrics}
        rows.append(row)
        if row["overall_workbench_edit_score"] < 0.75:
            failures.append(row)

    result_path = args.output_dir / "workbench_editing_v08_results.csv"
    with result_path.open("w", newline="", encoding="utf-8") as handle:
      writer = csv.DictWriter(handle, fieldnames=["case_id", "type", "prompt", *METRIC_COLUMNS])
      writer.writeheader()
      for row in rows:
          writer.writerow({key: row.get(key, "") for key in writer.fieldnames})

    summary = summarize_rows(rows)
    (args.output_dir / "workbench_editing_v08_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "workbench_editing_v08_failure_cases.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


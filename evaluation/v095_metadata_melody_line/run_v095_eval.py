"""Run the V0.95 metadata and melody-line benchmark."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from backend.generation.musicality.melody_line_extractor import extract_melody_lines
from backend.generation.musicality.melodic_grammar import repair_cross_measure_melody, validate_cross_measure_melody_events
from backend.pipeline import SeraPipeline
from backend.services.score_document_service import new_score_document, score_document_to_musicxml
from backend.services.score_note_event_service import score_document_to_playback_note_events
from backend.services.score_operation_service import apply_score_operation
from evaluation.v095_metadata_melody_line.metrics import (
    MELODY_COLUMNS,
    METADATA_COLUMNS,
    composer_edit_metrics,
    melody_metrics_from_reports,
    metadata_metrics_for_result,
    summarize,
)


ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = Path(__file__).resolve().parent
RESULTS = ROOT / "evaluation" / "results"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-prompts", type=int, default=3)
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    pipeline = SeraPipeline(ROOT)
    metadata_rows = run_title_key_cases(pipeline, args.max_prompts)
    metadata_rows.extend(run_composer_edit_cases())
    melody_rows = run_melody_line_cases(pipeline, args.max_prompts)
    melody_rows.extend(run_cross_measure_cases())
    melody_rows.append(run_mixed_playback_case())
    failures = {
        "metadata": [row for row in metadata_rows if any(float(row.get(column, 0.0)) < 1.0 for column in METADATA_COLUMNS if column != "composer_edit_success_rate")],
        "melody_line": [row for row in melody_rows if row.get("case_id") != "cross_measure_tritone" and float(row.get("melody_line_extraction_success_rate", 0.0)) < 1.0],
    }

    write_csv(RESULTS / "v095_metadata_results.csv", metadata_rows)
    write_csv(RESULTS / "v095_melody_line_results.csv", melody_rows)
    summary = {
        "metadata": summarize(metadata_rows, METADATA_COLUMNS),
        "melody_line": summarize(melody_rows, MELODY_COLUMNS),
        "rows": {"metadata": len(metadata_rows), "melody_line": len(melody_rows)},
    }
    (RESULTS / "v095_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v095_failure_cases.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "v095_table.tex").write_text(latex_table(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def run_title_key_cases(pipeline: SeraPipeline, max_prompts: int) -> list[dict[str, Any]]:
    rows = []
    for case in load_cases("title_key_cases.json")[:max_prompts]:
        result = pipeline.generate(
            case["prompt"],
            generator_mode="rule_based",
            ui_controls=case.get("ui_controls", {}),
            ui_control_sources=case.get("ui_control_sources", {}),
            control_policy={"prompt_priority": True, "allow_ui_defaults": True},
            musicality_controls={"variation_seed": case["id"]},
        )
        rows.append({"case_id": case["id"], "run_id": result.get("run_id", ""), **metadata_metrics_for_result(result)})
    return rows


def run_composer_edit_cases() -> list[dict[str, Any]]:
    rows = []
    for case in load_cases("composer_edit_cases.json"):
        score = new_score_document(title=case["title"], composer="Sera", key="C major", measures=1)
        score, _ = apply_score_operation(score, {"source": "user", "type": "change_title", "target": {"field": "title"}, "after": {"title": case["edited_title"]}, "description": "Change title"})
        score, _ = apply_score_operation(score, {"source": "user", "type": "change_composer", "target": {"field": "composer"}, "after": {"composer": case["edited_composer"]}, "description": "Change composer"})
        musicxml = score_document_to_musicxml(score)
        rows.append({"case_id": case["id"], "run_id": "", **composer_edit_metrics(musicxml, case["edited_composer"])})
    return rows


def run_melody_line_cases(pipeline: SeraPipeline, max_prompts: int) -> list[dict[str, Any]]:
    rows = []
    for case in load_cases("melody_line_cases.json")[:max_prompts]:
        result = pipeline.generate(case["prompt"], generator_mode="rule_based", musicality_controls={"variation_seed": case["id"]})
        metadata = result.get("generation_metadata", {})
        rows.append(
            {
                "case_id": case["id"],
                "run_id": result.get("run_id", ""),
                **melody_metrics_from_reports(metadata.get("melody_line_report", {}), metadata.get("cross_measure_melodic_grammar_report", {})),
            }
        )
    return rows


def run_cross_measure_cases() -> list[dict[str, Any]]:
    rows = []
    for case in load_cases("cross_measure_cases.json"):
        score = new_score_document(measures=2)
        score["measures"][0]["events"] = [case["from_event"]]
        score["measures"][1]["events"] = list(case["to_events"])
        melody_report = extract_melody_lines(score)
        primary = melody_report["primary_melody"]["events"]
        cross = validate_cross_measure_melody_events(primary, "C major", "major", {}, "beginner")
        repaired, repair_report = repair_cross_measure_melody(score, primary, "C major", "major", {}, "beginner")
        repaired_report = extract_melody_lines(repaired)
        repaired_cross = validate_cross_measure_melody_events(repaired_report["primary_melody"]["events"], "C major", "major", {}, "beginner")
        repaired_cross["repairs_applied"] = repair_report.get("repairs_applied", [])
        rows.append({"case_id": case["id"], "run_id": "", **melody_metrics_from_reports(melody_report, cross if case.get("expect_detection_only") else repaired_cross)})
    return rows


def run_mixed_playback_case() -> dict[str, Any]:
    score = new_score_document(measures=1)
    score["measures"][0]["events"] = [
        {"event_id": "rh1", "type": "note", "pitch": "C5", "duration": "quarter", "offset": 0.0, "voice": 1, "staff": "right_hand"},
        {"event_id": "lh1", "type": "note", "pitch": "C2", "duration": "quarter", "offset": 0.0, "voice": 1, "staff": "left_hand"},
    ]
    playback = score_document_to_playback_note_events(score)
    melody_report = extract_melody_lines(score)
    cross = validate_cross_measure_melody_events(melody_report["primary_melody"]["events"], "C major", "major", {}, "intermediate")
    row = {"case_id": "mixed_playback_not_melody", "run_id": "", **melody_metrics_from_reports(melody_report, cross)}
    row["playback_stream_not_melody"] = all(not event.get("melody_diagnostic_eligible") for event in playback)
    return row


def load_cases(name: str) -> list[dict[str, Any]]:
    return json.loads((CASE_DIR / name).read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def latex_table(summary: dict[str, Any]) -> str:
    lines = ["\\begin{tabular}{lr}", "Metric & Value \\\\", "\\hline"]
    for group, values in summary.items():
        if group == "rows":
            continue
        for key, value in values.items():
            lines.append(f"{group}.{key} & {value} \\\\")
    lines.append("\\end{tabular}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    main()

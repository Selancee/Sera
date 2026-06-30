"""Run V0.7 score-editing evaluation with mock-safe agent fallback."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.agents.score_editing_agent import ScoreEditingAgent
from backend.generation.rule_based_generator import RuleBasedGenerator
from backend.models.schemas import StructuredMusicIntent
from backend.services.score_document_service import musicxml_to_score_document
from backend.services.score_patch_service import ScorePatchService
from evaluation.score_editing.edit_metrics import METRIC_KEYS, row_from_edit_result, summarize_rows


def run_score_edit_eval(
    prompt_file: str | Path,
    out_csv: str | Path,
    out_summary: str | Path,
    out_failures: str | Path = "evaluation/results/score_editing_v07_failure_cases.json",
    max_prompts: int = 0,
) -> dict[str, float]:
    """Run the V0.7 score-editing prompt set."""

    prompts = json.loads(Path(prompt_file).read_text(encoding="utf-8"))
    if max_prompts:
        prompts = prompts[:max_prompts]
    plan = CompositionPlanningAgent().plan(StructuredMusicIntent(prompt="8 bar C major piano score editing seed", bars=8))
    score = RuleBasedGenerator().generate(plan)
    base_document = musicxml_to_score_document(score.musicxml, prompt=plan.intent.prompt, source="generated")
    agent = ScoreEditingAgent()
    service = ScorePatchService()
    rows = []
    failures = []
    for item in prompts:
        selected = {
            "start_measure": int(item.get("start_measure", 1)),
            "end_measure": int(item.get("end_measure", 1)),
            "part_id": "piano",
            "staff": item.get("staff", "right_hand"),
        }
        constraints = dict(item.get("constraints", {}))
        if item.get("task") == "explain":
            explanation = agent.explain_selection(base_document, selected, item["instruction"])
            metric_row = row_from_edit_result(
                {
                    "patch": {},
                    "validation_report": {"valid_musicxml": True, "warnings": []},
                    "prompt_alignment_score": {},
                    "accepted": True,
                    "explanation_success": 1.0 if explanation.get("summary") else 0.0,
                }
            )
            rows.append({"prompt_id": item.get("prompt_id", ""), "instruction": item["instruction"], **metric_row})
            continue
        patch = agent.create_patch(base_document, item["instruction"], selected, constraints)
        result = service.apply_patch(base_document, patch, item["instruction"], selected, constraints)
        partial = service.partial_apply_patch(
            base_document,
            patch,
            operation_indexes=[0] if patch.get("operations") else [],
            instruction=item["instruction"],
            selected_range=selected,
            constraints=constraints,
        )
        result["partial_apply_success"] = 1.0 if partial.get("accepted") else 0.0
        result["agent_trace"] = agent.last_trace
        metric_row = row_from_edit_result(result)
        rows.append({"prompt_id": item.get("prompt_id", ""), "instruction": item["instruction"], **metric_row})
        if not result.get("accepted") or metric_row["prompt_alignment_edit_score"] < 0.7:
            failures.append(
                {
                    "prompt_id": item.get("prompt_id", ""),
                    "instruction": item["instruction"],
                    "accepted": result.get("accepted"),
                    "patch_validation_report": result.get("patch_validation_report", {}),
                    "metrics": metric_row,
                }
            )
    _write_csv(out_csv, rows)
    summary = summarize_rows(rows)
    target = Path(out_summary)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    failure_target = Path(out_failures)
    failure_target.parent.mkdir(parents=True, exist_ok=True)
    failure_target.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _write_csv(path: str | Path, rows: list[dict[str, object]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["prompt_id", "instruction", *METRIC_KEYS]
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default="evaluation/score_editing/edit_prompt_sets_v07.json")
    parser.add_argument("--out-csv", default="evaluation/results/score_editing_v07_results.csv")
    parser.add_argument("--out-summary", default="evaluation/results/score_editing_v07_summary.json")
    parser.add_argument("--out-failures", default="evaluation/results/score_editing_v07_failure_cases.json")
    parser.add_argument("--max-prompts", type=int, default=0)
    args = parser.parse_args()
    summary = run_score_edit_eval(args.prompts, args.out_csv, args.out_summary, args.out_failures, max_prompts=args.max_prompts)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

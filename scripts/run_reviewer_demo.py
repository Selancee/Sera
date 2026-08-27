#!/usr/bin/env python3
"""Run a compact, offline SoftwareX reviewer demonstration.

The demo exercises the same product entry point, transaction, protected-scope checks,
source-preserving MusicXML export and round-trip import used by the desktop application.
Gold patches are never supplied to generation; benchmark constraints are used only for
deterministic post-run verification.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.runners.runtime_acceptance_runner import run_runtime_acceptance


DEFAULT_TASKS = (
    "pitch_001",
    "dynamics_001",
    "key_001",
    "meter_001",
    "voice_010",
    "conflict_001",
)


def run_reviewer_demo(
    output_dir: Path,
    *,
    task_ids: Sequence[str] = DEFAULT_TASKS,
    languages: Sequence[str] = ("en",),
) -> dict[str, Any]:
    """Run or resume the bounded offline demo and return its audit report."""

    output_dir = output_dir.resolve()
    selected_tasks = list(dict.fromkeys(str(task_id) for task_id in task_ids))
    selected_languages = list(dict.fromkeys(str(language) for language in languages))
    if not selected_tasks:
        raise ValueError("at least one reviewer-demo task is required")
    summary = run_runtime_acceptance(
        benchmark_root=ROOT / "benchmark",
        split_name="core",
        experiment_dir=output_dir,
        mode="local",
        task_ids=selected_tasks,
        languages=selected_languages,
        repetitions=1,
        host_scope_mode="exact",
        latest_report_path=None,
    )
    results = dict(summary["results"])
    expected_runs = len(selected_tasks) * len(selected_languages)
    host_outputs = sorted((output_dir / "host_outputs").glob("*.musicxml"))
    passed = (
        results.get("tasks") == expected_runs
        and results.get("passed") == expected_runs
        and results.get("failed") == 0
        and results.get("musicxml_validity") == 1.0
        and summary.get("gold_used_for_generation") is False
        and summary.get("mode") == "local"
    )
    report = {
        "schema_version": "1.0.0",
        "passed": passed,
        "evidence_class": "offline_reviewer_demonstration",
        "network_used": False,
        "gold_used_for_generation": False,
        "gold_used_for_deterministic_evaluation_only": True,
        "tasks": selected_tasks,
        "languages": selected_languages,
        "results": results,
        "host_openable_output_count": len(host_outputs),
        "host_openable_outputs": [str(path.relative_to(output_dir)).replace("\\", "/") for path in host_outputs],
        "artifacts": {
            "manifest": "manifest.json",
            "runs": "runs.jsonl",
            "metrics": "metrics.csv",
            "failures": "failures.csv",
            "summary": "summary.json",
            "raw_outputs": "raw_outputs/",
            "host_outputs": "host_outputs/",
        },
        "claim_boundary": (
            "This demonstration verifies offline product-path behavior and MusicXML round trips; "
            "it is not a remote-LLM accuracy or musical-aesthetics experiment."
        ),
    }
    report_path = output_dir / "reviewer_demo_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts" / "softwarex_reviewer_demo",
        help="Directory for resumable raw, metric and MusicXML evidence.",
    )
    parser.add_argument("--task", action="append", dest="tasks", help="Core task ID; repeatable.")
    parser.add_argument(
        "--language",
        action="append",
        choices=("en", "zh"),
        dest="languages",
        help="Instruction language; repeatable (default: en).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_reviewer_demo(
        args.output_dir,
        task_ids=args.tasks or DEFAULT_TASKS,
        languages=args.languages or ("en",),
    )
    results = report["results"]
    print(
        f"SoftwareX reviewer demo: {results['passed']}/{results['tasks']} passed; "
        f"host MusicXML outputs={report['host_openable_output_count']}; "
        f"report={args.output_dir.resolve() / 'reviewer_demo_report.json'}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

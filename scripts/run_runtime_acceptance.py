"""Replay benchmark tasks through the actual interactive Sera patch pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.runners.runtime_acceptance_runner import ROOT, run_runtime_acceptance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, default=ROOT / "benchmark")
    parser.add_argument("--split", default="core", help="Benchmark split name without .json")
    parser.add_argument(
        "--mode",
        choices=("local", "configured"),
        default="local",
        help="local forbids network use; configured follows the desktop provider settings",
    )
    parser.add_argument("--experiment-id", help="Stable ID to create or resume")
    parser.add_argument("--task", action="append", dest="task_ids", help="Run only this split task; repeatable")
    parser.add_argument(
        "--language",
        action="append",
        choices=("en", "zh"),
        dest="languages",
        help="Instruction language to replay; repeat for bilingual acceptance (default: en)",
    )
    parser.add_argument(
        "--fail-on-task-failure",
        action="store_true",
        help="Return exit code 1 if any selected task fails product acceptance",
    )
    parser.add_argument("--repetitions", type=int, default=1, help="Repeat every task/language pair (default: 1)")
    parser.add_argument(
        "--host-scope-mode",
        choices=("exact", "expanded_adjacent"),
        default="exact",
        help="expanded_adjacent widens eligible explicit-measure host selections by one adjacent measure",
    )
    args = parser.parse_args()
    experiment_id = args.experiment_id or (
        f"runtime_acceptance_{args.split}_{args.mode}_"
        f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    )
    summary = run_runtime_acceptance(
        benchmark_root=args.benchmark_root,
        split_name=args.split,
        experiment_dir=ROOT / "experiments" / experiment_id,
        mode=args.mode,
        task_ids=args.task_ids,
        languages=args.languages,
        repetitions=args.repetitions,
        host_scope_mode=args.host_scope_mode,
        latest_report_path=(
            args.benchmark_root
            / "validation"
            / (
                f"{args.split}_runtime_acceptance_latest.json"
                if args.host_scope_mode == "exact"
                else f"{args.split}_runtime_acceptance_host_scope_latest.json"
            )
        ),
    )
    results = summary["results"]
    print(
        f"{experiment_id}: {results['passed']}/{results['tasks']} runs passed "
        f"across {results['unique_tasks']} tasks; "
        f"failures={results['failed']}; p95={results['p95_latency_ms']:.1f} ms"
    )
    if args.fail_on_task_failure and results["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

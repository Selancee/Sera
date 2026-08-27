"""Run/resume a configured multi-provider repeated SeraEdit experiment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.runners.experiment_runner import run_experiment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="A local config copied from full.example.yaml")
    parser.add_argument("--experiment-id", help="Override output ID; a matching existing run is resumed")
    args = parser.parse_args()
    summary = run_experiment(args.config.resolve(), experiment_id=args.experiment_id)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["completed_runs"] == summary["expected_runs"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

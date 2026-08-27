"""Generate paired statistical and error-taxonomy reports for one experiment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.error_analysis.taxonomy import build_error_taxonomy
from evaluation.statistics.paired_analysis import analyze_experiment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Experiment ID under experiments/")
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    experiment_dir = ROOT / "experiments" / args.experiment
    report = analyze_experiment(experiment_dir, bootstrap_samples=args.bootstrap_samples, seed=args.seed)
    taxonomy = build_error_taxonomy(experiment_dir / "metrics.csv", experiment_dir / "error_taxonomy.csv")
    print(json.dumps({"experiment_id": report["experiment_id"], "groups": len(report["groups"]), "taxonomy_rows": len(taxonomy)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

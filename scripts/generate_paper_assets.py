"""Generate SeraEdit paper tables, statistics, captions, and figures from one experiment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.reporting.paper_assets import generate_paper_assets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Experiment ID under experiments/")
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    args = parser.parse_args()
    result = generate_paper_assets(ROOT, args.experiment, bootstrap_samples=args.bootstrap_samples)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

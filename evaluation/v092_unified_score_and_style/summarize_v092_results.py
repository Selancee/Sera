"""Print a compact summary for V0.92 evaluation results."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "results" / "v092_summary.json"
    if not path.exists():
        raise SystemExit("Run evaluation.v092_unified_score_and_style.run_v092_eval first.")
    print(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))


if __name__ == "__main__":
    main()

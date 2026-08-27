from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "results" / "v091_usability_summary.json"
    print(path.read_text(encoding="utf-8") if path.exists() else json.dumps({"error": "run V0.91 eval first"}))


if __name__ == "__main__":
    main()

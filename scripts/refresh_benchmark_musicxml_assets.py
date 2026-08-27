"""Refresh derived benchmark MusicXML from canonical ScoreDocument JSON.

This command deliberately leaves tasks, Gold patches, deterministic diffs,
review records, and canonical score JSON unchanged. It is used when the
MusicXML host-boundary serializer improves without changing benchmark
semantics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.score_document_service import score_document_to_musicxml


def _refresh_directory(directory: Path, pattern: str) -> int:
    count = 0
    for score_path in sorted(directory.glob(pattern)):
        score = json.loads(score_path.read_text(encoding="utf-8"))
        target = score_path.with_suffix("").with_suffix(".musicxml")
        target.write_text(score_document_to_musicxml(score), encoding="utf-8")
        count += 1
    return count


def refresh(benchmark_root: Path) -> dict[str, int]:
    return {
        "source_scores": _refresh_directory(benchmark_root / "source_scores", "score_*.score.json"),
        "expected_outputs": _refresh_directory(benchmark_root / "expected_outputs", "*.score.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-root",
        type=Path,
        default=ROOT / "benchmark",
        help="Benchmark directory containing source_scores and expected_outputs.",
    )
    args = parser.parse_args()
    result = refresh(args.benchmark_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

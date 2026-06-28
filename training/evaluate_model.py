"""Evaluate generated MusicXML outputs from a model checkpoint or baseline.

TODO: Extend this to evaluate decoder-only Transformer generations from PDMX,
MetaScore, POP909, and Lakh MIDI Dataset derived test splits.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.metrics import aggregate_metrics, validate_musicxml_file


def main() -> None:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", default="examples/scores")
    parser.add_argument("--out", default="data/processed/model_eval.json")
    args = parser.parse_args()

    rows = []
    for path in sorted(Path(args.scores).glob("*.musicxml")):
        metrics = validate_musicxml_file(path)
        rows.append(
            {
                "run_id": path.stem,
                "musicxml_validity": 1.0 if metrics["valid"] else 0.0,
                "musicxml_validity_rate": 1.0 if metrics["valid"] else 0.0,
                "bar_completeness": metrics.get("bar_completeness", 0.0),
                "bar_completeness_score": metrics.get("bar_completeness_score", 0.0),
                "pitch_range_validity": 1.0 if metrics.get("pitch_range_valid") else 0.0,
                "pitch_range_validity_rate": 1.0 if metrics.get("pitch_range_valid") else 0.0,
                "midi_export_success_rate": 0.0,
                "pdf_export_success_rate": 0.0,
                "empty_measure_rate": metrics.get("empty_measure_count", 0) / max(1, metrics.get("measure_count", 1)),
                "prompt_adherence_rule_score": 0.0,
                "revision_success_rate": 0.0,
            }
        )
    result = {"runs": rows, "aggregate": aggregate_metrics(rows)}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

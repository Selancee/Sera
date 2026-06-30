"""Diagnostics for generated Sera MusicXML artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.analysis.music_statistics import diagnose_directory, write_distribution_csv


def run_generated_music_diagnostics(
    input_dir: str | Path = "examples/scores",
    output_dir: str | Path = "evaluation/results",
    max_files: int = 0,
) -> dict:
    """Analyze generated MusicXML files and write V0.5 reports."""

    out = Path(output_dir)
    report = diagnose_directory(
        input_dir=input_dir,
        output_json=out / "generated_music_diagnostics.json",
        max_files=max_files,
    )
    rows = report.get("files", [])
    write_distribution_csv(out / "rhythm_distribution.csv", rows, "rhythm_distribution")
    write_distribution_csv(out / "pitch_interval_distribution.csv", rows, "pitch_interval_distribution")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="examples/scores")
    parser.add_argument("--output_dir", default="evaluation/results")
    parser.add_argument("--max_files", type=int, default=0)
    args = parser.parse_args()
    report = run_generated_music_diagnostics(args.input_dir, args.output_dir, args.max_files)
    print(f"Wrote generated-music diagnostics for {report['summary'].get('file_count', 0)} files")


if __name__ == "__main__":
    main()

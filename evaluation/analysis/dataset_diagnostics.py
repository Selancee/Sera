"""Dataset diagnostics for Sera V0.5 training corpora."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.analysis.music_statistics import diagnose_directory, write_distribution_csv


def run_dataset_diagnostics(
    input_dir: str | Path = "data",
    output_dir: str | Path = "evaluation/results",
    max_files: int = 0,
) -> dict:
    """Analyze MusicXML files in a dataset directory and write V0.5 reports."""

    out = Path(output_dir)
    report = diagnose_directory(
        input_dir=input_dir,
        output_json=out / "dataset_diagnostics.json",
        max_files=max_files,
    )
    rows = report.get("files", [])
    write_distribution_csv(out / "rhythm_distribution.csv", rows, "rhythm_distribution")
    write_distribution_csv(out / "pitch_interval_distribution.csv", rows, "pitch_interval_distribution")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="data")
    parser.add_argument("--output_dir", default="evaluation/results")
    parser.add_argument("--max_files", type=int, default=0)
    args = parser.parse_args()
    report = run_dataset_diagnostics(args.input_dir, args.output_dir, args.max_files)
    print(f"Wrote dataset diagnostics for {report['summary'].get('file_count', 0)} files")


if __name__ == "__main__":
    main()

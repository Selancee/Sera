"""Build a secret-scanned anonymous SeraEdit research package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".json", ".jsonl", ".yaml", ".yml", ".md", ".py", ".txt", ".csv", ".tex", ".bib", ".mmd"}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
]


def _selected_files(experiment_id: str) -> Iterable[Path]:
    roots = [
        ROOT / "benchmark",
        ROOT / "sera_edit",
        ROOT / "evaluation" / "conditions",
        ROOT / "evaluation" / "configs",
        ROOT / "evaluation" / "error_analysis",
        ROOT / "evaluation" / "metrics",
        ROOT / "evaluation" / "reporting",
        ROOT / "evaluation" / "runners",
        ROOT / "evaluation" / "statistics",
        ROOT / "paper" / "figures",
        ROOT / "paper" / "tables",
        ROOT / "paper" / "manuscript",
        ROOT / "paper" / "supplementary",
    ]
    files = [
        ROOT / "README.md",
        ROOT / "pyproject.toml",
        ROOT / "requirements.txt",
        ROOT / "evaluation" / "benchmark_io.py",
        ROOT / "evaluation" / "SERAEDIT_EXPERIMENTS.md",
        ROOT / "paper" / "ASSET_MANIFEST.json",
    ]
    files.extend(ROOT / "scripts" / name for name in (
        "validate_benchmark.py",
        "run_smoke_experiment.py",
        "run_core_experiment.py",
        "run_full_experiment.py",
        "recompute_metrics.py",
        "analyze_experiment.py",
        "generate_paper_assets.py",
        "verify_reproducibility.py",
        "export_anonymous_package.py",
    ))
    experiment = ROOT / "experiments" / experiment_id
    files.extend(experiment / name for name in (
        "manifest.json", "config_snapshot.yaml", "runs.jsonl", "metrics.csv", "metrics_recomputed.csv",
        "summary.json", "errors.csv", "statistics.json", "statistics.md", "error_taxonomy.csv",
        "recompute_manifest.json", "reproducibility_report.json", "reproducibility_report.md",
    ))
    roots.append(experiment / "normalized_outputs")
    for path in files:
        if path.exists() and path.is_file():
            yield path
    for root in roots:
        if root.exists():
            yield from (path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts)


def _redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in {"request_id"}:
                result[key] = "[REDACTED FOR ANONYMITY]" if item else item
            elif key == "git" and isinstance(item, dict):
                result[key] = {"commit": "[REDACTED FOR ANONYMITY]", "dirty": item.get("dirty")}
            else:
                result[key] = _redact_json(item)
        return result
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    return value


def _copy_redacted(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".json":
        try:
            payload = json.loads(source.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            shutil.copy2(source, destination)
        else:
            destination.write_text(json.dumps(_redact_json(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif source.suffix.lower() == ".jsonl":
        output = []
        for line in source.read_text(encoding="utf-8").splitlines():
            output.append(json.dumps(_redact_json(json.loads(line)), ensure_ascii=False))
        destination.write_text("\n".join(output) + "\n", encoding="utf-8")
    else:
        shutil.copy2(source, destination)


def _scan(staging: Path) -> list[str]:
    findings: list[str] = []
    for path in staging.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            findings.append(str(path.relative_to(staging)).replace("\\", "/"))
    return findings


def build_package(experiment_id: str, output: Path) -> dict[str, Any]:
    """Create one deterministic file manifest and compressed anonymous archive."""

    with tempfile.TemporaryDirectory(prefix="seraedit_anonymous_") as temporary:
        staging = Path(temporary) / "seraedit_anonymous"
        copied: set[str] = set()
        for source in _selected_files(experiment_id):
            relative = str(source.relative_to(ROOT)).replace("\\", "/")
            if relative in copied:
                continue
            _copy_redacted(source, staging / relative)
            copied.add(relative)
        findings = _scan(staging)
        if findings:
            raise RuntimeError(f"possible credential material found in: {', '.join(findings)}")
        entries = []
        for path in sorted(item for item in staging.rglob("*") if item.is_file()):
            data = path.read_bytes()
            entries.append(
                {
                    "path": str(path.relative_to(staging)).replace("\\", "/"),
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        release_manifest = {
            "package": "SeraEdit anonymous research release",
            "experiment_id": experiment_id,
            "file_count": len(entries),
            "raw_provider_outputs_included": False,
            "normalized_outputs_included": True,
            "files": entries,
        }
        (staging / "ANONYMOUS_RELEASE_MANIFEST.json").write_text(
            json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in staging.rglob("*") if item.is_file()):
                archive.write(path, arcname=str(path.relative_to(staging)).replace("\\", "/"))
    return {
        "experiment_id": experiment_id,
        "output": str(output.relative_to(ROOT)).replace("\\", "/"),
        "file_count": release_manifest["file_count"] + 1,
        "secret_scan_findings": 0,
        "raw_provider_outputs_included": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Experiment ID under experiments/")
    parser.add_argument("--output", help="Destination ZIP path")
    args = parser.parse_args()
    default = ROOT / "paper" / "anonymous_release" / f"seraedit_anonymous_{args.experiment}.zip"
    output = Path(args.output).resolve() if args.output else default
    print(json.dumps(build_package(args.experiment, output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

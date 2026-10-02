#!/usr/bin/env python3
"""Verify manifest bytes and execute the offline reviewer path from an isolated ZIP extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def extract_verified(archive_path: Path, destination: Path) -> dict:
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP members")
        for name in names:
            target = (destination / name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError(f"ZIP member escapes destination: {name}")
        manifest = json.loads(archive.read("SOFTWAREX_ARCHIVE_MANIFEST.json"))
        declared = {entry["path"] for entry in manifest["files"]}
        if len(declared) != len(manifest["files"]) or set(names) != declared | {"SOFTWAREX_ARCHIVE_MANIFEST.json"}:
            raise ValueError("ZIP contents differ from the archive manifest")
        for entry in manifest["files"]:
            data = archive.read(entry["path"])
            if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError(f"archive file integrity failure: {entry['path']}")
        archive.extractall(destination)
    return manifest


def verify_archive(archive_path: Path, output_dir: Path, *, skip_tests: bool = False) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    checks = {}
    with tempfile.TemporaryDirectory(prefix="seraedit_source_archive_") as temporary:
        root = Path(temporary)
        manifest = extract_verified(archive_path, root)
        commands = {
            "reproducibility": ["scripts/verify_reproducibility.py", "--experiment", "softwarex_revision_verification_120_v2", "--skip-tests", "--output-dir", str(output_dir / "reproducibility")],
            "reviewer_demo": ["scripts/run_reviewer_demo.py", "--output-dir", str(root / "artifacts/reviewer_demo")],
            "pytest": ["-m", "pytest", "-q", f"--junitxml={output_dir / 'pytest.xml'}"],
        }
        if skip_tests:
            commands["pytest"] = ["-m", "pytest", "--collect-only", "-q"]
        for name, command in commands.items():
            result = subprocess.run([sys.executable, *command], cwd=root, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            log = result.stdout + "\n" + result.stderr
            (output_dir / f"{name}.log").write_text(log, encoding="utf-8")
            checks[name] = {"passed": result.returncode == 0, "return_code": result.returncode, "output_tail": log.strip().splitlines()[-15:]}
        demo = root / "artifacts/reviewer_demo/reviewer_demo_report.json"
        if demo.is_file():
            (output_dir / "reviewer_demo_report.json").write_bytes(demo.read_bytes())
    report = {
        "archive": archive_path.name,
        "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "manifest_files_verified": len(manifest["files"]),
        "source_git": manifest["git"],
        "isolated_source_extraction": True,
        "dependency_environment": "existing interpreter; not a fresh dependency installation",
        "python_version": sys.version,
        "full_tests_executed": not skip_tests,
        "checks": checks,
        "passed": all(check["passed"] for check in checks.values()),
    }
    (output_dir / "archive_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--skip-tests", action="store_true", help="Collect tests without executing them; still run the verifier and reviewer demo")
    args = parser.parse_args()
    report = verify_archive(args.archive.resolve(), args.output_dir.resolve(), skip_tests=args.skip_tests)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

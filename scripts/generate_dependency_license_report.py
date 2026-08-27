#!/usr/bin/env python3
"""Generate a direct-dependency license inventory for the SoftwareX package."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata as metadata
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGES = (
    "fastapi", "uvicorn", "pydantic", "python-dotenv", "requests", "pytest",
    "PyYAML", "httpx2", "pyinstaller", "music21", "mido", "pretty_midi", "partitura",
    "python-docx",
)
NODE_PACKAGES = {
    "frontend": ("react", "react-dom", "vite", "vexflow", "opensheetmusicdisplay"),
    "electron": ("electron", "electron-builder"),
}


def python_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name in PYTHON_PACKAGES:
        try:
            package = metadata.metadata(name)
            license_name = package.get("License-Expression") or package.get("License") or "UNKNOWN"
            rows.append({
                "ecosystem": "python",
                "name": name,
                "version": metadata.version(name),
                "license": license_name.splitlines()[0].strip(),
                "source": "active virtual environment",
            })
        except metadata.PackageNotFoundError:
            rows.append({"ecosystem": "python", "name": name, "version": "NOT_INSTALLED", "license": "UNKNOWN", "source": "active virtual environment"})
    return rows


def node_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for workspace, packages in NODE_PACKAGES.items():
        for name in packages:
            path = root / workspace / "node_modules" / name / "package.json"
            if path.is_file():
                package = json.loads(path.read_text(encoding="utf-8"))
                rows.append({"ecosystem": "npm", "name": name, "version": str(package.get("version", "UNKNOWN")), "license": str(package.get("license", "UNKNOWN")), "source": str(path.relative_to(root))})
            else:
                rows.append({"ecosystem": "npm", "name": name, "version": "NOT_INSTALLED", "license": "UNKNOWN", "source": str(path.relative_to(root))})
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate SoftwareX direct-dependency license CSV and JSON files.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "paper" / "softwarex")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = python_rows() + node_rows(ROOT)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "dependency_licenses.csv"
    json_path = args.output_dir / "dependency_licenses.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("ecosystem", "name", "version", "license", "source"))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps({"generated_from": "installed direct dependencies", "rows": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "csv": str(csv_path), "json": str(json_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

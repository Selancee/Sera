#!/usr/bin/env python3
"""Verify frozen SoftwareX submission files without writing or rebuilding them."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT / "paper/softwarex/baselines/submission_2026-08-28/BASELINE_MANIFEST.json"
)


def verify_baseline(
    manifest_path: Path, *, root: Path = ROOT, include_local_archives: bool = False
) -> dict:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    checked = {"submission_files": 0, "local_archives": 0}
    if manifest.get("schema_version") != 1 or not manifest.get("files"):
        errors.append("Invalid or empty baseline manifest")

    def check(entries: list[dict], base: Path, group: str) -> None:
        base = base.resolve()
        for entry in entries:
            relative = Path(entry["path"])
            target = (base / relative).resolve()
            if relative.is_absolute() or not target.is_relative_to(base):
                errors.append(f"{group}: path escapes baseline: {entry['path']}")
                continue
            checked[group] += 1
            if not target.is_file():
                errors.append(f"{group}: missing file: {entry['path']}")
                continue
            content = target.read_bytes()
            if len(content) != entry["bytes"]:
                errors.append(f"{group}: size mismatch: {entry['path']}")
            if hashlib.sha256(content).hexdigest() != entry["sha256"]:
                errors.append(f"{group}: SHA-256 mismatch: {entry['path']}")

    check(manifest.get("files", []), manifest_path.parent, "submission_files")
    if include_local_archives:
        check(manifest.get("local_archives", []), root, "local_archives")
    return {
        "passed": not errors,
        "baseline_id": manifest.get("baseline_id"),
        "checked": checked,
        "editorial_manager_original_files_verified": manifest.get(
            "editorial_manager_original_files_verified", False
        ),
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--include-local-archives", action="store_true",
        help="Also require the local source/release archive copies under artifacts/.",
    )
    args = parser.parse_args(argv)
    try:
        result = verify_baseline(
            args.manifest, include_local_archives=args.include_local_archives
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Baseline verification failed: {exc}")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

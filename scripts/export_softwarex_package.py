#!/usr/bin/env python3
"""Create deterministic SoftwareX source and manuscript ZIP archives.

Only explicit publication paths are eligible. User settings, API keys, build outputs,
node_modules, model weights, and unrelated historic experiments are excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0-dev.14"
FIXED_ZIP_TIME = (2026, 8, 23, 0, 0, 0)
MAX_FILE_BYTES = 20 * 1024 * 1024

ROOT_FILES = (
    ".env.example", "LICENSE", "THIRD_PARTY_NOTICES.md", "CITATION.cff",
    "codemeta.json", "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
    "pyproject.toml", "requirements.txt", "requirements-tested-windows.txt",
    "requirements-training.txt", "requirements-publication.txt",
)
SOURCE_TREES = (
    ".github", "backend", "sera_edit", "frontend", "electron", "integrations/musescore",
    "benchmark", "demo", "scripts", "tests", "packaging/windows",
    "docs/softwarex", "docs/architecture", "evaluation/conditions",
    "evaluation/metrics", "evaluation/runners", "evaluation/statistics",
    "evaluation/error_analysis", "evaluation/reporting", "evaluation/configs",
    "experiments/softwarex_verification_120_v1",
    "experiments/softwarex_runtime_acceptance_720_v4",
    "experiments/softwarex_host_scope_robustness_240_v3", "paper/softwarex",
    "experiments/softwarex_human_review_120_v1",
)
MANUSCRIPT_TREES = (
    "paper/softwarex/manuscript", "paper/softwarex/figures",
    "paper/softwarex/submission", "docs/softwarex",
    "experiments/softwarex_human_review_120_v1",
)
EXCLUDED_PARTS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "dist",
    "build", "coverage", ".vite", "release", "release-dev14",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".key", ".pem", ".pfx"}
SENSITIVE_NAMES = {".env", "llm.env", "credentials.json", "secrets.json"}
SECRET_RE = re.compile(
    rb"(?:sk-[A-Za-z0-9_-]{16,}|BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|"
    rb"api[_-]?key\s*[:=]\s*['\"][^'\"]{12,})",
    re.IGNORECASE,
)
SAFE_SECRET_MARKERS = (
    b"<set outside source control>", b"<redacted>", b"<your", b"[your",
    b"placeholder", b"example", b"dummy", b"fake", b"test-", b"secret-only",
    b"in-app-secret",
)


def eligible(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        path.is_file()
        and not any(part in EXCLUDED_PARTS for part in relative.parts)
        and path.name.lower() not in SENSITIVE_NAMES
        and path.suffix.lower() not in EXCLUDED_SUFFIXES
        and path.stat().st_size <= MAX_FILE_BYTES
    )


def collect(paths: tuple[str, ...], root_files: tuple[str, ...] = ()) -> list[Path]:
    found: set[Path] = set()
    for value in root_files:
        path = ROOT / value
        if eligible(path):
            found.add(path)
    for value in paths:
        base = ROOT / value
        if base.is_file() and eligible(base):
            found.add(base)
        elif base.is_dir():
            found.update(path for path in base.rglob("*") if eligible(path))
    return sorted(found, key=lambda path: path.relative_to(ROOT).as_posix())


def assert_safe(files: list[Path]) -> None:
    for path in files:
        relative = path.relative_to(ROOT)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe archive path: {relative}")
        payload = path.read_bytes()
        for match in SECRET_RE.finditer(payload):
            candidate = match.group(0).lower()
            if any(marker in candidate for marker in SAFE_SECRET_MARKERS):
                continue
            raise ValueError(f"Possible secret in publication file: {relative}")


def git_state() -> dict[str, object]:
    def command(*args: str) -> str:
        return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    return {
        "commit": command("git", "rev-parse", "HEAD"),
        "dirty": bool(command("git", "status", "--porcelain")),
    }


def file_manifest(files: list[Path]) -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in files
    ]


def write_entry(archive: ZipFile, name: str, payload: bytes) -> None:
    info = ZipInfo(PurePosixPath(name).as_posix(), FIXED_ZIP_TIME)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, payload)


def write_archive(path: Path, files: list[Path], kind: str) -> dict[str, object]:
    entries = file_manifest(files)
    manifest = {
        "package": "SeraEdit",
        "version": VERSION,
        "kind": kind,
        "license": "MIT",
        "benchmark_license": "CC0-1.0",
        "git": git_state(),
        "file_count": len(entries),
        "total_bytes": sum(int(entry["bytes"]) for entry in entries),
        "files": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as archive:
        for source in files:
            write_entry(archive, source.relative_to(ROOT).as_posix(), source.read_bytes())
        write_entry(archive, "SOFTWAREX_ARCHIVE_MANIFEST.json", (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    manifest["archive"] = str(path)
    manifest["archive_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export deterministic SoftwareX source and LaTeX submission archives.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "paper" / "softwarex" / "release")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_files = collect(SOURCE_TREES, ROOT_FILES)
    manuscript_files = collect(MANUSCRIPT_TREES, ("CITATION.cff", "LICENSE"))
    assert_safe(source_files)
    assert_safe(manuscript_files)
    source_manifest = write_archive(args.output_dir / f"seraedit-{VERSION}-source.zip", source_files, "source_distribution")
    manuscript_manifest = write_archive(args.output_dir / f"seraedit-{VERSION}-softwarex-manuscript.zip", manuscript_files, "manuscript_sources")
    payload = {"source": source_manifest, "manuscript": manuscript_manifest}
    manifest_path = args.output_dir / "release_manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "source_archive": source_manifest["archive"],
        "source_files": source_manifest["file_count"],
        "source_sha256": source_manifest["archive_sha256"],
        "manuscript_archive": manuscript_manifest["archive"],
        "manuscript_files": manuscript_manifest["file_count"],
        "manuscript_sha256": manuscript_manifest["archive_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

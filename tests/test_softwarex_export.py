import hashlib
import json
from pathlib import Path

import pytest

from scripts.export_softwarex_package import (
    MANUSCRIPT_TREES,
    ROOT,
    assert_safe,
    collect,
    eligible,
    preserved_source_manifest,
)


def test_export_excludes_secrets_builds_and_dependencies(tmp_path):
    assert not eligible(ROOT / ".env") if (ROOT / ".env").exists() else True
    assert not eligible(ROOT / "frontend" / "node_modules" / "react" / "package.json")
    assert not eligible(ROOT / "frontend" / "dist" / "index.html")


def test_minimal_publication_selection_is_safe():
    files = collect(("docs/softwarex",), ("LICENSE", "CITATION.cff"))
    assert files
    assert all(path.is_relative_to(ROOT) for path in files)
    assert_safe(files)


def test_manuscript_package_includes_frozen_human_review_evidence():
    files = collect(MANUSCRIPT_TREES, ("CITATION.cff", "LICENSE"))
    relative_paths = {path.relative_to(ROOT).as_posix() for path in files}
    assert "experiments/softwarex_human_review_120_v1/summary.json" in relative_paths
    assert "experiments/softwarex_human_review_120_v1/evidence_manifest.json" in relative_paths


def test_preserved_source_manifest_requires_matching_published_archive(tmp_path):
    archive = tmp_path / "seraedit-1.0.0-source.zip"
    archive.write_bytes(b"published-source")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (tmp_path / "release_manifest.json").write_text(
        json.dumps({"source": {"archive_sha256": digest, "file_count": 1}}),
        encoding="utf-8",
    )

    source = preserved_source_manifest(tmp_path)

    assert source["archive_sha256"] == digest
    assert source["preserved_published_artifact"] is True
    assert source["archive"] == str(archive)


def test_preserved_source_manifest_refuses_digest_drift(tmp_path):
    archive = tmp_path / "seraedit-1.0.0-source.zip"
    archive.write_bytes(b"changed-source")
    (tmp_path / "release_manifest.json").write_text(
        json.dumps({"source": {"archive_sha256": "0" * 64}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not match"):
        preserved_source_manifest(tmp_path)

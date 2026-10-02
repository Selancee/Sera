import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from scripts.verify_softwarex_source_archive import extract_verified

from scripts.export_softwarex_package import (
    MANUSCRIPT_TREES,
    SOURCE_TREES,
    ROOT_FILES,
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


def test_source_package_contains_required_evaluation_modules_and_hash_policy():
    files = {path.relative_to(ROOT).as_posix() for path in collect(SOURCE_TREES, ROOT_FILES)}
    assert {
        ".gitattributes", "evaluation/benchmark_io.py",
        "evaluation/analysis/music_statistics.py",
        "evaluation/runners/experiment_runner.py",
        "evaluation/configs/softwarex_revision_mock.yaml",
        "tests/sera_edit/test_reproducibility_contract.py",
    } <= files


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


def test_source_archive_verification_rejects_changed_member_bytes(tmp_path):
    archive = tmp_path / "source.zip"
    manifest = {"files": [{"path": "a.py", "bytes": 4, "sha256": hashlib.sha256(b"good").hexdigest()}]}
    with ZipFile(archive, "w") as output:
        output.writestr("SOFTWAREX_ARCHIVE_MANIFEST.json", json.dumps(manifest))
        output.writestr("a.py", b"evil")
    with pytest.raises(ValueError, match="integrity failure"):
        extract_verified(archive, tmp_path / "extract")


def test_source_archive_verification_rejects_path_escape(tmp_path):
    archive = tmp_path / "source.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("../outside.py", b"data")
    with pytest.raises(ValueError, match="escapes destination"):
        extract_verified(archive, tmp_path / "extract")

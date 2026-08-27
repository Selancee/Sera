from pathlib import Path

from scripts.export_softwarex_package import (
    MANUSCRIPT_TREES,
    ROOT,
    assert_safe,
    collect,
    eligible,
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

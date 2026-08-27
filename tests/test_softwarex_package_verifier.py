from pathlib import Path

from scripts.verify_softwarex_package import (
    abstract_word_count,
    keyword_count,
    main_text_word_count,
    normalized_version,
    versions_match,
)


def test_version_normalization_accepts_python_and_desktop_forms():
    versions = {
        "python": "1.0.0.dev14",
        "backend": "1.0.0-dev.14",
        "frontend": "1.0.0-dev.14",
        "electron": "1.0.0-dev.14",
    }
    assert normalized_version("1.0.0.dev14") == "1.0.0-dev.14"
    assert versions_match(versions)


def test_manuscript_counts_only_numbered_main_sections():
    text = """# Title
## Abstract
One two three four.
Keywords: a; b; c
## 1. Motivation
Five words live in body.
## 2. Software
Another four body words.
## Code metadata
These words do not count.
"""
    assert main_text_word_count(text) == 9
    assert abstract_word_count(text) == 4
    assert keyword_count(text) == 3


def test_required_softwarex_tree_is_workspace_relative():
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "softwarex" / "publication.yml").is_file()
    assert (root / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")

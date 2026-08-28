from pathlib import Path

from scripts.verify_softwarex_package import (
    archive_submission_blockers,
    abstract_word_count,
    highlight_lengths,
    has_required_ai_disclosure,
    keyword_count,
    main_text_word_count,
    normalized_version,
    valid_email,
    valid_archive_doi,
    valid_mit_license,
    valid_orcid,
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


def test_highlight_lengths_count_characters_and_optional_bullet_markers():
    text = "Short highlight.\n- Another highlight with spaces.\n\n"
    assert highlight_lengths(text) == [16, 30]


def test_ai_disclosure_requires_heading_and_author_responsibility_in_both_sources():
    disclosure = (
        "Declaration of generative AI and AI-assisted technologies in the manuscript preparation process\n"
        "The author takes full responsibility for\nthe content of the publication."
    )
    assert has_required_ai_disclosure(disclosure, disclosure)
    assert not has_required_ai_disclosure(disclosure, "")


def test_required_softwarex_tree_is_workspace_relative():
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "softwarex" / "publication.yml").is_file()
    assert (root / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_mit_license_verification_accepts_real_owner_and_rejects_incomplete_text():
    root = Path(__file__).resolve().parents[1]
    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    assert "Copyright (c) 2026 Yuan Gao" in license_text
    assert valid_mit_license(license_text)
    assert not valid_mit_license("MIT License\n\nCopyright (c) 2026 Yuan Gao\n")


def test_orcid_validation_uses_iso_7064_checksum():
    assert valid_orcid("0009-0005-0394-3623")
    assert valid_orcid("https://orcid.org/0009-0005-0394-3623")
    assert not valid_orcid("0009-0005-0394-3624")
    assert not valid_orcid("[ORCID]")


def test_support_email_validation_rejects_placeholders_and_malformed_values():
    assert valid_email("selanceg@gmail.com")
    assert not valid_email("[SUPPORT EMAIL]")
    assert not valid_email("selanceg@gmail")


def test_archive_doi_reservation_does_not_unlock_submission():
    publication = {
        "archive_doi": "10.5281/zenodo.22128976",
        "archive_url": "https://doi.org/10.5281/zenodo.22128976",
        "archive_status": "reserved",
        "archive_published": False,
    }
    assert valid_archive_doi(publication["archive_doi"])
    assert archive_submission_blockers(publication) == [
        "permanent archive DOI is reserved but archive is not yet published"
    ]


def test_published_archive_doi_unlocks_archive_gate():
    publication = {
        "archive_doi": "10.5281/zenodo.22128976",
        "archive_url": "https://doi.org/10.5281/zenodo.22128976",
        "archive_status": "published",
        "archive_published": True,
    }
    assert archive_submission_blockers(publication) == []


def test_archive_doi_requires_canonical_url_and_value():
    assert not valid_archive_doi("https://doi.org/10.5281/zenodo.22128976")
    assert archive_submission_blockers({"archive_doi": "not-a-doi"}) == [
        "permanent archive DOI is invalid",
        "permanent archive URL does not match archive DOI",
        "permanent archive DOI is reserved but archive is not yet published",
    ]


def test_tested_windows_constraints_pin_direct_dependencies():
    root = Path(__file__).resolve().parents[1]
    lines = [
        line.strip()
        for line in (root / "requirements-tested-windows.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    names = [line.split("==", 1)[0].lower() for line in lines]
    assert all("==" in line for line in lines)
    assert len(names) == len(set(names))
    assert {"fastapi", "pydantic", "pytest", "music21", "python-docx"} <= set(names)


def test_reviewer_commands_place_npm_prefix_before_the_script_separator():
    root = Path(__file__).resolve().parents[1]
    for relative in (
        "docs/softwarex/INSTALLATION.md",
        "docs/softwarex/REVIEWER_GUIDE.md",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "npm.cmd --prefix frontend test -- --run" in text
        assert "npm.cmd test -- --run --prefix frontend" not in text

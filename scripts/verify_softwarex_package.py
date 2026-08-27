#!/usr/bin/env python3
"""Verify the local SoftwareX release and manuscript package.

The draft profile checks technical completeness.  The submission profile also
requires author-owned public-release metadata and intentionally fails until those
facts are supplied; it never invents an identity, DOI, or public availability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "paper" / "softwarex" / "package_verification.json"
PLACEHOLDER_RE = re.compile(r"\[[A-Z][A-Z0-9 _/-]*\]")

REQUIRED_FILES = (
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CITATION.cff",
    "codemeta.json",
    "docs/softwarex/INSTALLATION.md",
    "docs/softwarex/USER_MANUAL.md",
    "docs/softwarex/API_REFERENCE.md",
    "docs/softwarex/REPRODUCIBILITY.md",
    "docs/softwarex/SOFTWAREX_REQUIREMENTS_MATRIX.md",
    "experiments/softwarex_runtime_acceptance_720_v4/summary.json",
    "experiments/softwarex_runtime_acceptance_720_v4/evidence_manifest.json",
    "experiments/softwarex_host_scope_robustness_240_v3/summary.json",
    "experiments/softwarex_host_scope_robustness_240_v3/evidence_manifest.json",
    "experiments/softwarex_human_review_120_v1/summary.json",
    "experiments/softwarex_human_review_120_v1/evidence_manifest.json",
    "paper/softwarex/manuscript/seraedit_softwarex.md",
    "paper/softwarex/manuscript/seraedit_softwarex.tex",
    "paper/softwarex/manuscript/seraedit_softwarex.docx",
    "paper/softwarex/manuscript/references.bib",
    "paper/softwarex/figures/figure1_architecture.mmd",
    "paper/softwarex/figures/figure1_architecture.svg",
    "paper/softwarex/submission/COVER_LETTER.md",
    "paper/softwarex/submission/HIGHLIGHTS.txt",
    "paper/softwarex/submission/DECLARATION_OF_INTEREST.md",
    "paper/softwarex/submission/CREDIT_AUTHOR_STATEMENT.md",
    "paper/softwarex/submission/GENERATIVE_AI_DISCLOSURE.md",
    "paper/softwarex/submission/DATA_AND_CODE_AVAILABILITY.md",
)


@dataclass
class VerificationResult:
    profile: str
    passed: bool = True
    checks: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    submission_blockers: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.errors.append(message)
        self.passed = False


def normalized_version(value: str) -> str:
    return value.replace(".dev", "-dev.").replace("-dev.", "-dev.")


def read_versions(root: Path) -> dict[str, str]:
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    backend_text = (root / "backend" / "app.py").read_text(encoding="utf-8")
    match = re.search(r'^BACKEND_VERSION\s*=\s*"([^"]+)"', backend_text, re.MULTILINE)
    if not match:
        raise ValueError("BACKEND_VERSION not found")
    return {
        "python": str(pyproject["project"]["version"]),
        "backend": match.group(1),
        "frontend": json.loads((root / "frontend" / "package.json").read_text(encoding="utf-8"))["version"],
        "electron": json.loads((root / "electron" / "package.json").read_text(encoding="utf-8"))["version"],
        "citation": str(yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))["version"]),
        "codemeta": str(json.loads((root / "codemeta.json").read_text(encoding="utf-8"))["version"]),
    }


def versions_match(versions: dict[str, str]) -> bool:
    canonical = {normalized_version(value).replace("-dev.14", "-dev14") for value in versions.values()}
    return len(canonical) == 1


def main_text_word_count(markdown: str) -> int:
    """Count words in numbered OSP Sections 1-5, excluding tables and captions."""
    start = re.search(r"^##\s+1\.", markdown, re.MULTILINE)
    end = re.search(r"^##\s+(?:Code metadata|Acknowledg|Author contributions|References)", markdown, re.MULTILINE)
    if not start:
        return 0
    body = markdown[start.start() : end.start() if end else len(markdown)]
    body = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    body = re.sub(r"^#{1,6}\s+.*$", " ", body, flags=re.MULTILINE)
    body = re.sub(r"^\|.*$", " ", body, flags=re.MULTILINE)
    body = re.sub(r"!\[[^]]*\]\([^)]*\)", " ", body)
    body = re.sub(r"\[[^]]+\]\([^)]*\)", " ", body)
    return len(re.findall(r"\b[\w][\w'-]*\b", body, flags=re.UNICODE))


def abstract_word_count(markdown: str) -> int:
    match = re.search(r"^## Abstract\s+(.*?)(?=^Keywords:|^##\s)", markdown, re.MULTILINE | re.DOTALL)
    if not match:
        return 0
    return len(re.findall(r"\b[\w][\w'-]*\b", match.group(1), flags=re.UNICODE))


def keyword_count(markdown: str) -> int:
    match = re.search(r"^Keywords:\s*(.+)$", markdown, re.MULTILINE)
    return len([item for item in match.group(1).split(";") if item.strip()]) if match else 0


def _manifest_hashes_match(directory: Path, manifest: dict[str, Any]) -> bool:
    files = manifest.get("files") or []
    if not files or manifest.get("file_count") != len(files):
        return False
    for item in files:
        path = directory / str(item.get("path", ""))
        if not path.is_file():
            return False
        if path.stat().st_size != item.get("bytes"):
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != item.get("sha256"):
            return False
    return True


def verify(root: Path, profile: str) -> VerificationResult:
    result = VerificationResult(profile=profile)

    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    result.checks["required_files"] = {"missing": missing, "count": len(REQUIRED_FILES)}
    if missing:
        result.fail(f"Missing required files: {', '.join(missing)}")

    try:
        versions = read_versions(root)
        match = versions_match(versions)
        result.checks["version_consistency"] = {"passed": match, "versions": versions}
        if not match:
            result.fail("Python, backend, frontend, Electron, CFF and CodeMeta versions differ")
    except Exception as exc:  # pragma: no cover - defensive reporting
        result.checks["version_consistency"] = {"passed": False, "error": str(exc)}
        result.fail(f"Cannot verify versions: {exc}")

    license_text = (root / "LICENSE").read_text(encoding="utf-8") if (root / "LICENSE").exists() else ""
    license_ok = license_text.startswith("MIT License") and "Sera contributors" in license_text
    result.checks["software_license"] = {"passed": license_ok, "spdx": "MIT" if license_ok else None}
    if not license_ok:
        result.fail("Root MIT license is missing or incomplete")

    manuscript_path = root / "paper" / "softwarex" / "manuscript" / "seraedit_softwarex.md"
    manuscript = manuscript_path.read_text(encoding="utf-8") if manuscript_path.exists() else ""
    words = main_text_word_count(manuscript)
    abstract_words = abstract_word_count(manuscript)
    keywords = keyword_count(manuscript)
    result.checks["manuscript_limits"] = {
        "main_text_words": words,
        "main_text_limit": 3000,
        "abstract_words": abstract_words,
        "abstract_target": "approximately 100",
        "keywords": keywords,
        "keyword_limit": 6,
    }
    if words == 0 or words > 3000:
        result.fail(f"SoftwareX main text word count is {words}; expected 1-3000")
    if not 70 <= abstract_words <= 130:
        result.warnings.append(f"Abstract has {abstract_words} words; journal template requests approximately 100")
    if not 1 <= keywords <= 6:
        result.fail(f"Keyword count is {keywords}; expected 1-6")

    figure_dir = root / "paper" / "softwarex" / "figures"
    figures = sorted(path.name for path in figure_dir.glob("figure*.svg")) if figure_dir.exists() else []
    result.checks["figures"] = {"count": len(figures), "files": figures, "limit": 6}
    if len(figures) > 6:
        result.fail("More than six numbered manuscript figures are present")

    summary_path = root / "experiments" / "softwarex_verification_120_v1" / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        experiment_ok = (
            summary.get("completed_runs") == 360
            and summary.get("expected_runs") == 360
            and summary.get("error_count") == 0
            and summary.get("formal_results_allowed") is False
        )
        result.checks["software_verification_experiment"] = {
            "passed": experiment_ok,
            "completed_runs": summary.get("completed_runs"),
            "expected_runs": summary.get("expected_runs"),
            "error_count": summary.get("error_count"),
            "result_class": summary.get("result_class"),
            "formal_results_allowed": summary.get("formal_results_allowed"),
        }
        if not experiment_ok:
            result.fail("SoftwareX verification experiment is incomplete or mislabeled")
    else:
        result.checks["software_verification_experiment"] = {"passed": False, "missing": str(summary_path)}
        result.fail("SoftwareX verification experiment summary is missing")

    runtime_summary_path = root / "experiments" / "softwarex_runtime_acceptance_720_v4" / "summary.json"
    runtime_manifest_path = root / "experiments" / "softwarex_runtime_acceptance_720_v4" / "evidence_manifest.json"
    if runtime_summary_path.exists() and runtime_manifest_path.exists():
        runtime_summary = json.loads(runtime_summary_path.read_text(encoding="utf-8"))
        runtime_manifest = json.loads(runtime_manifest_path.read_text(encoding="utf-8"))
        runtime_results = runtime_summary.get("results") or {}
        reproducibility = runtime_results.get("reproducibility") or {}
        cross_language = runtime_results.get("cross_language_equivalence") or {}
        host_export = runtime_results.get("source_preserving_host_export") or {}
        runtime_ok = (
            runtime_results.get("tasks") == 720
            and runtime_results.get("passed") == 720
            and runtime_results.get("failed") == 0
            and runtime_results.get("unique_tasks") == 120
            and runtime_results.get("musicxml_validity") == 1.0
            and runtime_results.get("complete_preservation_rate") == 1.0
            and host_export.get("expected") == 660
            and host_export.get("succeeded") == 660
            and host_export.get("failed") == 0
            and reproducibility.get("rate") == 1.0
            and cross_language.get("task_groups") == 120
            and cross_language.get("semantic_patch_rate") == 1.0
            and cross_language.get("output_rate") == 1.0
            and runtime_summary.get("paper_model_result_eligible") is False
            and runtime_summary.get("gold_used_for_generation") is False
            and runtime_manifest.get("raw_output_count") == 720
            and runtime_manifest.get("host_output_count") == 660
            and runtime_manifest.get("review_host_output_count") == 220
        )
        result.checks["product_runtime_acceptance"] = {
            "passed": runtime_ok,
            "runs": runtime_results.get("tasks"),
            "tasks": runtime_results.get("unique_tasks"),
            "failed": runtime_results.get("failed"),
            "reproducibility_rate": reproducibility.get("rate"),
            "cross_language_output_rate": cross_language.get("output_rate"),
            "source_preserving_host_export": host_export,
            "complete_preservation_rate": runtime_results.get("complete_preservation_rate"),
            "paper_model_result_eligible": runtime_summary.get("paper_model_result_eligible"),
            "hashed_evidence_files": runtime_manifest.get("full_evidence_file_count"),
            "review_host_outputs": runtime_manifest.get("review_host_output_count"),
        }
        if not runtime_ok:
            result.fail("Product runtime acceptance evidence is incomplete, failed, or mislabeled")
    else:
        result.checks["product_runtime_acceptance"] = {"passed": False}
        result.fail("Product runtime acceptance publication snapshot is missing")

    scope_summary_path = root / "experiments" / "softwarex_host_scope_robustness_240_v3" / "summary.json"
    scope_manifest_path = root / "experiments" / "softwarex_host_scope_robustness_240_v3" / "evidence_manifest.json"
    if scope_summary_path.exists() and scope_manifest_path.exists():
        scope_summary = json.loads(scope_summary_path.read_text(encoding="utf-8"))
        scope_manifest = json.loads(scope_manifest_path.read_text(encoding="utf-8"))
        scope_results = scope_summary.get("results") or {}
        scope_stress = scope_results.get("scope_stress") or {}
        cross_language = scope_results.get("cross_language_equivalence") or {}
        host_export = scope_results.get("source_preserving_host_export") or {}
        scope_ok = (
            scope_summary.get("host_scope_mode") == "expanded_adjacent"
            and scope_results.get("tasks") == 240
            and scope_results.get("passed") == 240
            and scope_results.get("failed") == 0
            and scope_results.get("unique_tasks") == 120
            and scope_results.get("musicxml_validity") == 1.0
            and scope_results.get("complete_preservation_rate") == 1.0
            and host_export.get("expected") == 220
            and host_export.get("succeeded") == 220
            and host_export.get("failed") == 0
            and scope_stress.get("runs_applied") == 174
            and scope_stress.get("runs_passed") == 174
            and cross_language.get("task_groups") == 120
            and cross_language.get("output_rate") == 1.0
            and scope_summary.get("paper_model_result_eligible") is False
            and scope_summary.get("gold_used_for_generation") is False
            and scope_manifest.get("raw_output_count") == 240
            and scope_manifest.get("host_output_count") == 220
            and scope_manifest.get("review_host_output_count") == 220
        )
        result.checks["host_scope_robustness"] = {
            "passed": scope_ok,
            "runs": scope_results.get("tasks"),
            "failed": scope_results.get("failed"),
            "expanded_runs": scope_stress.get("runs_applied"),
            "expanded_runs_passed": scope_stress.get("runs_passed"),
            "cross_language_output_rate": cross_language.get("output_rate"),
            "source_preserving_host_export": host_export,
            "complete_preservation_rate": scope_results.get("complete_preservation_rate"),
            "hashed_evidence_files": scope_manifest.get("full_evidence_file_count"),
        }
        if not scope_ok:
            result.fail("Host-scope robustness evidence is incomplete, failed, or mislabeled")
    else:
        result.checks["host_scope_robustness"] = {"passed": False}
        result.fail("Host-scope robustness publication snapshot is missing")

    human_dir = root / "experiments" / "softwarex_human_review_120_v1"
    human_summary_path = human_dir / "summary.json"
    human_manifest_path = human_dir / "evidence_manifest.json"
    human_ok = False
    if human_summary_path.exists() and human_manifest_path.exists():
        human_summary = json.loads(human_summary_path.read_text(encoding="utf-8"))
        human_manifest = json.loads(human_manifest_path.read_text(encoding="utf-8"))
        hashes_ok = _manifest_hashes_match(human_dir, human_manifest)
        human_ok = (
            human_summary.get("evidence_class") == "human_benchmark_task_review"
            and human_summary.get("review_complete") is True
            and human_summary.get("total_tasks") == 120
            and human_summary.get("primary_reviewed") == 120
            and human_summary.get("secondary_reviewed") == 30
            and human_summary.get("secondary_target") == 30
            and human_summary.get("stale_records") == 0
            and human_summary.get("remaining") == 0
            and human_summary.get("record_count") == human_summary.get("csv_record_count")
            and hashes_ok
        )
        result.checks["human_benchmark_review"] = {
            "passed": human_ok,
            "primary_reviewed": human_summary.get("primary_reviewed"),
            "secondary_reviewed": human_summary.get("secondary_reviewed"),
            "stale_records": human_summary.get("stale_records"),
            "decisions": human_summary.get("decisions"),
            "record_count": human_summary.get("record_count"),
            "independent_secondary_reviewer": human_summary.get("independent_secondary_reviewer"),
            "hashes_match": hashes_ok,
            "claim_boundary": human_summary.get("claim_boundary"),
        }
        if not human_summary.get("independent_secondary_reviewer"):
            result.warnings.append(
                "The 30-task secondary check was repeated by the same pseudonymous reviewer; "
                "do not report inter-rater reliability"
            )
        if not human_ok:
            result.fail("Human benchmark-review evidence is incomplete or has drifted")
    else:
        result.checks["human_benchmark_review"] = {"passed": False}
        result.fail("Human benchmark-review publication snapshot is missing")

    config_path = root / "docs" / "softwarex" / "publication.yml"
    publication = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    blockers: list[str] = []
    if not publication.get("repository_public"):
        blockers.append("GitHub repository is not confirmed public")
    if not publication.get("release_tag"):
        blockers.append("immutable release tag is missing")
    if not publication.get("archive_doi"):
        blockers.append("permanent archive DOI is missing")
    if not publication.get("license_owner_confirmed"):
        blockers.append("copyright owner has not confirmed the MIT release")
    if not publication.get("benchmark_human_review_complete") or not human_ok:
        blockers.append("completed human benchmark review is not confirmed by frozen evidence")
    for key in ("author_name", "affiliation", "support_email"):
        value = str(publication.get(key, ""))
        if not value or PLACEHOLDER_RE.search(value):
            blockers.append(f"publication field {key} is not supplied")
    result.submission_blockers = blockers
    result.checks["submission_metadata"] = {"passed": not blockers, "blockers": blockers}
    if profile == "submission" and blockers:
        result.fail("Author-owned publication metadata is incomplete")
    elif blockers:
        result.warnings.append("Draft is technically complete but not submission-ready")

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify SeraEdit's SoftwareX manuscript and software package.")
    parser.add_argument("--profile", choices=("draft", "submission"), default="draft")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = verify(ROOT, args.profile)
    payload = asdict(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())

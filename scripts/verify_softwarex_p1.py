#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the local R1 document bundle without treating publication gates as passed."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R1 = ROOT / "paper/softwarex/revisions/2026-10_minor_r1"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def normalized(text: str) -> str:
    return " ".join(text.split())


def section(text: str, heading: str) -> str:
    return text.split(heading + "\n", 1)[1].split("\n## ", 1)[0].strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manuscript = (R1 / "manuscript/seraedit_softwarex.md").read_text(encoding="utf-8")
    fields = (R1 / "submission/EDITORIAL_MANAGER_FILL_IN.md").read_text(encoding="utf-8")
    abstract = section(manuscript, "## Abstract").split("Keywords:")[0].strip()
    keywords = manuscript.split("Keywords: ", 1)[1].splitlines()[0]
    body = manuscript.split("## 1. ", 1)[1].split("## Code metadata", 1)[0]
    # Tables and captions are included; author metadata and references are excluded.
    body = body.split("## Software metadata", 1)[0].split("## References", 1)[0]
    body = body.split("## 6. ", 1)[0]
    body = re.sub(r"^!\[.*?\]\(.*?\)$", "", body, flags=re.M)
    body = re.sub(r"^\|[ :|\-]+$", "", body, flags=re.M)
    body = re.sub(r"[#|*`]", " ", body)
    counts = {"abstract_words": len(abstract.split()), "main_words": len(body.split()),
              "keywords": len(keywords.split(";")), "figures": len(re.findall(r"^!\[", manuscript, re.M))}
    checks: dict[str, bool] = {}
    checks["title_synchronized"] = manuscript.splitlines()[0][2:] == section(fields, "## Title")
    checks["abstract_synchronized"] = normalized(abstract) == normalized(section(fields, "## Abstract"))
    checks["keywords_synchronized"] = normalized(keywords) == normalized(section(fields, "## Keywords"))
    checks["conservative_length_targets"] = counts["abstract_words"] <= 250 and counts["main_words"] <= 3000 and counts["keywords"] == 6 and counts["figures"] <= 6
    checks["primary_references_present"] = all(x in manuscript for x in ("2310.06770", "2312.12450", "2505.08203v1", "handbook.musescore.org/customization/plugins"))
    checks["canonical_eight_checks_present"] = normalized("source binding, schema, structure and addressing, measure duration, notation relations, declared semantic conditions, protected scope, and MusicXML round-trip fidelity") in normalized(manuscript)
    checks["platform_versions_and_boundary"] = all(x in manuscript for x in ("3.12.5", "24.16.0", "11.13.0", "Windows", "POSIX", "unsaved in-memory changes"))
    checks["run_task_distinction"] = all(x in manuscript for x in ("240/240 bilingual runs", "174 runs", "remaining 66 runs", "not 720 independent tasks"))
    declaration = (R1 / "submission/DECLARATION_OF_INTEREST.md").read_text(encoding="utf-8")
    checks["interest_heading_matches"] = declaration.splitlines()[0][2:] in manuscript
    highlights = (R1 / "submission/HIGHLIGHTS.txt").read_text(encoding="utf-8").splitlines()
    checks["highlights_limits"] = 3 <= len(highlights) <= 5 and all(len(line) <= 85 for line in highlights)

    with (ROOT / "experiments/softwarex_deepseek_core_20261002_v1/metrics.csv").open(encoding="utf-8", newline="") as handle:
        metrics = list(csv.DictReader(handle))
    observed = {}
    for condition, label in (("full_rewrite", "Full Rewrite"), ("patch_only", "Patch Only"), ("sera_full", "Sera Full")):
        rows = [r for r in metrics if r["condition"] == condition and r["expected_status"] != "refuse"]
        outputs = [r for r in rows if int(r["output_produced"]) and not int(r["refused"])]
        strict = sum(float(r["constraint_satisfaction"]) == 1 and int(r["complete_preservation"]) == 1 and r["musicxml_validity"] == "1" for r in outputs)
        leaks = sum(int(r["complete_preservation"]) != 1 for r in outputs)
        refused = sum(int(r["refused"]) for r in rows)
        observed[condition] = {"strict_success": strict, "executable": len(rows), "outputs": len(outputs), "leaked_outputs": leaks, "erroneous_refusals": refused}
        table_row = next(line for line in manuscript.splitlines() if line.startswith(f"| {label} |"))
        checks[f"{condition}_table_matches_saved_metrics"] = all(token in table_row for token in (f"{strict}/{len(rows)}", f"| {len(outputs)} |", f"{leaks}/{len(outputs)}", f"{refused}/{len(rows)}"))
    checks["negative_evidence_and_scope_explicit"] = all(x in normalized(manuscript) for x in ("do not demonstrate higher overall editing success", "3/20", "180/180", "regression evidence", "25 repaired editing tasks ended in erroneous refusal"))

    hashes = json.loads((R1 / "UI_EVIDENCE_HASHES.json").read_text(encoding="utf-8"))
    checks["six_actual_screenshot_hashes"] = len(hashes) == 6 and all(digest(R1 / "figures" / name) == item["sha256"] for name, item in hashes.items())
    for relative in ("manuscript/seraedit_softwarex.docx", "RESPONSE_TO_REVIEWERS.docx", "submission/COVER_LETTER.docx"):
        with zipfile.ZipFile(R1 / relative) as package:
            document = ET.fromstring(package.read("word/document.xml"))
            styles = ET.fromstring(package.read("word/styles.xml"))
            checks[f"{relative}_no_paragraph_border"] = not document.findall(".//w:pBdr", NS) and not styles.findall(".//w:pBdr", NS)
            if relative.startswith("manuscript"):
                paragraphs = ["".join(p.itertext()) for p in document.findall(".//w:p", NS)]
                checks["eleven_separate_reference_paragraphs"] = sum(bool(re.match(r"^\[\d+\] ", p)) for p in paragraphs) == 11
                checks["three_embedded_figures"] = len([p for p in package.namelist() if p.startswith("word/media/")]) == 3

    inventory = json.loads((R1 / "SOURCE_LICENSE_INVENTORY.json").read_text(encoding="utf-8"))
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
    expected = {p for p in tracked if Path(p).suffix in extensions}
    checks["license_sidecar_coverage"] = {x["path"] for x in inventory["files"]} == expected
    checks["license_sidecar_hashes"] = all(x["SPDX-License-Identifier"] == "MIT" and digest(ROOT / x["path"]) == x["sha256"] for x in inventory["files"])

    with (R1 / "REVIEWER_COMMENT_MATRIX.csv").open(encoding="utf-8", newline="") as handle:
        matrix = list(csv.DictReader(handle))
    p1 = [row for row in matrix if next(iter(row.values())).startswith("P1-")]
    checks["eight_p1_items_mapped"] = len(p1) == 8
    report = {"local_checks_passed": all(checks.values()), "overall_p1_status": "partial_open_gates",
              "scope": "Local document consistency and artifact integrity; no new API call, hosted CI or publication.",
              "counts": counts, "saved_metrics": observed, "checks": checks,
              "open_gates": ["Actual MuseScore plugin send/open-revision visual evidence", "Revised public archive/DOI and hosted CI"],
              "reasoned_alternative": "File-level SPDX sidecar supplied; reviewer acceptance of this alternative to inline headers is not established.",
              "submission_gates": ["Author review and marked manuscript", "Editorial Manager original-upload and assembled-PDF verification"]}
    (R1 / "P1_ACCEPTANCE.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["local_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

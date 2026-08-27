"""Versioned SeraEdit failure taxonomy and experiment counts."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any


ERROR_TAXONOMY = {
    "E01": ("malformed_xml", "roundtrip"),
    "E02": ("musicxml_parse_failure", "roundtrip"),
    "E03": ("malformed_patch_json", "parse"),
    "E04": ("patch_schema_failure", "schema"),
    "E05": ("invalid_selector", "structural"),
    "E06": ("missing_event", "structural"),
    "E07": ("duration_mismatch", "duration"),
    "E08": ("voice_collision", "notation"),
    "E09": ("broken_tie", "notation"),
    "E10": ("broken_slur", "notation"),
    "E11": ("protected_scope_violation", "protected_scope"),
    "E12": ("unintended_pitch_change", "semantic"),
    "E13": ("unintended_duration_change", "semantic"),
    "E14": ("unintended_notation_change", "roundtrip_fidelity"),
    "E15": ("incomplete_instruction_execution", "semantic"),
    "E16": ("over_editing", "metrics"),
    "E17": ("hallucinated_measure_or_voice", "structural"),
    "E18": ("conflicting_instruction_not_refused", "refusal"),
    "E19": ("unsupported_operation", "schema"),
    "E20": ("timeout_or_provider_error", "provider"),
}


def build_error_taxonomy(metrics_path: Path, output_path: Path) -> list[dict[str, Any]]:
    """Count primary/secondary codes from a metrics CSV and write all known codes."""

    counts: Counter[str] = Counter()
    primary: Counter[str] = Counter()
    with metrics_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            codes = [code.strip() for code in str(row.get("error_codes") or "").split(";") if code.strip()]
            counts.update(codes)
            if codes:
                primary[codes[0]] += 1
    rows = [
        {
            "error_code": code,
            "name": name,
            "default_stage": stage,
            "occurrences": counts[code],
            "primary_occurrences": primary[code],
        }
        for code, (name, stage) in ERROR_TAXONOMY.items()
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows

from __future__ import annotations

import json
from pathlib import Path

from scripts.export_runtime_acceptance_evidence import ROOT, export_runtime_evidence


def test_compact_runtime_evidence_snapshot_is_complete_and_non_formal(tmp_path: Path) -> None:
    source = ROOT / "experiments" / "runtime_acceptance_core_bilingual_r3_v3_20260825"
    payload = export_runtime_evidence(source, tmp_path / "snapshot")

    summary = json.loads((tmp_path / "snapshot" / "summary.json").read_text(encoding="utf-8"))
    assert summary["results"]["passed"] == 720
    assert summary["results"]["failed"] == 0
    assert payload["paper_model_result_eligible"] is False
    assert payload["gold_used_for_generation"] is False
    assert payload["raw_output_count"] == 720
    assert payload["host_output_count"] == 660
    assert len(payload["representative_files"]) == 38
    assert payload["review_host_output_count"] == 220
    assert len(list((tmp_path / "snapshot" / "review_host_outputs").glob("*.musicxml"))) == 220

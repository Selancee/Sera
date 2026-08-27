"""Verify meter_001 through a running packaged Sera backend and host export."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.score_document_service import musicxml_to_score_document  # noqa: E402
from evaluation.benchmark_io import load_task  # noqa: E402
from scripts.validate_benchmark import evaluate_constraints  # noqa: E402


def _request(base_url: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            content_type = response.headers.get("Content-Type", "")
            return json.loads(body) if "json" in content_type else body
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} returned HTTP {exc.code}: {detail}") from exc


def verify(base_url: str) -> dict[str, Any]:
    benchmark_root = ROOT / "benchmark"
    task = load_task(benchmark_root, "meter_001", "core")
    source_musicxml = (
        benchmark_root / "source_scores" / f"{task['score_id']}.musicxml"
    ).read_text(encoding="utf-8")
    created = _request(
        base_url,
        "/integrations/notation-sessions",
        {
            "host_id": "musescore",
            "musicxml": source_musicxml,
            "source_name": "meter_001.musicxml",
            "host_context": {
                "selection": {
                    "is_range": True,
                    "start_measure": 1,
                    "end_measure": 3,
                }
            },
        },
    )
    session_id = str(created["session"]["session_id"])
    source_score = created["score_document"]
    generated = _request(
        base_url,
        "/sera-edit/generate-preview",
        {
            "score_document": source_score,
            "instruction": task["instruction_en"],
            # Match the desktop Agent exactly: the host contributes a selected
            # measure range, not the benchmark's already-canonical whole-score scope.
            "target_scope": {"measures": [1, 2, 3]},
            "protected_scope": task["protected_scope"],
        },
    )
    operation_types = [operation["type"] for operation in (generated.get("patch") or {}).get("operations", [])]
    if generated.get("status") != "generated" or operation_types != ["change_time_signature", "delete_event"]:
        raise RuntimeError(f"meter_001 generation was incomplete: {operation_types}")
    if (generated.get("preview") or {}).get("validation_report", {}).get("status") != "valid":
        raise RuntimeError("meter_001 preview did not validate")
    if not (generated.get("patch") or {}).get("target_scope", {}).get("whole_score"):
        raise RuntimeError("meter_001 host selection was not promoted for its global meter operation")
    preview_diff = generated["preview"]["diff"]
    if preview_diff.get("global_changes", {}).get("meter") != {"before": "4/4", "after": "3/4"}:
        raise RuntimeError(f"meter_001 preview did not expose the meter diff: {preview_diff}")
    if len(preview_diff.get("deleted") or []) != 6:
        raise RuntimeError(f"meter_001 preview did not expose six deletions: {preview_diff}")

    applied = _request(
        base_url,
        "/sera-edit/apply",
        {"score_document": source_score, "patch": generated["patch"]},
    )
    if not applied.get("committed"):
        raise RuntimeError(f"meter_001 transaction did not commit: {applied.get('rollback_reason')}")
    exported = _request(
        base_url,
        f"/integrations/notation-sessions/{session_id}/export",
        {"score_document": applied["score_document"], "expected_revision": 0},
    )
    reparsed = musicxml_to_score_document(exported["musicxml"], source="packaged_meter_roundtrip")
    valid, errors = evaluate_constraints(source_score, reparsed, task["expected_constraints"])
    if not valid:
        raise RuntimeError(f"meter_001 host round-trip constraints failed: {errors}")
    event_count = sum(len(measure.get("events") or []) for measure in reparsed.get("measures") or [])
    result = {
        "passed": True,
        "session_id": session_id,
        "generation_status": generated["status"],
        "scope_resolution": generated["patch"]["provenance"]["scope_resolution"],
        "target_whole_score": generated["patch"]["target_scope"]["whole_score"],
        "operation_types": operation_types,
        "validation_status": generated["preview"]["validation_report"]["status"],
        "preview_global_changes": preview_diff["global_changes"],
        "preview_deleted_count": len(preview_diff["deleted"]),
        "revision": exported["revision"],
        "export_mode": exported["export_mode"],
        "changed_global_fields": exported["source_preservation"]["changed_global_fields"],
        "deleted_event_ids": sorted(exported["source_preservation"]["changed_event_ids"]),
        "meter": reparsed["global"]["meter"],
        "event_count": event_count,
        "constraint_errors": errors,
    }
    if result["revision"] != 1 or result["meter"] != "3/4" or event_count != 19:
        raise RuntimeError(f"meter_001 packaged result mismatch: {result}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    print(json.dumps(verify(args.base_url), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

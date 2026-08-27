"""Verify staff-local voice edits through a running packaged Sera backend."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.score_document_service import musicxml_to_score_document  # noqa: E402
from evaluation.benchmark_io import load_task  # noqa: E402
from scripts.validate_benchmark import evaluate_constraints  # noqa: E402
from sera_edit.execution.diff_engine import score_diff  # noqa: E402


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
            return json.loads(body) if "json" in response.headers.get("Content-Type", "") else body
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} returned HTTP {exc.code}: {detail}") from exc


def _raw_lanes_by_measure(musicxml: str) -> dict[int, list[list[int]]]:
    root = ET.fromstring(musicxml)
    result: dict[int, list[list[int]]] = {}
    for measure in root.findall(".//measure"):
        lanes = {
            (int(note.findtext("./staff") or 1), int(note.findtext("./voice") or 1))
            for note in measure.findall("./note")
            if note.find("./pitch") is not None
        }
        result[int(measure.get("number") or 0)] = [list(lane) for lane in sorted(lanes)]
    return result


def _verify_task(base_url: str, task_id: str, expected_lanes: dict[int, list[list[int]]]) -> dict[str, Any]:
    benchmark_root = ROOT / "benchmark"
    task = load_task(benchmark_root, task_id, "core")
    source_musicxml = (
        benchmark_root / "source_scores" / f"{task['score_id']}.musicxml"
    ).read_text(encoding="utf-8")
    created = _request(
        base_url,
        "/integrations/notation-sessions",
        {
            "host_id": "musescore",
            "musicxml": source_musicxml,
            "source_name": f"{task_id}.musicxml",
            "host_context": {
                "selection": {"is_range": True, "start_measure": 1, "end_measure": 3}
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
            "target_scope": {"measures": [1, 2, 3], "staffs": [1, 2]},
            "protected_scope": task["protected_scope"],
        },
    )
    patch = generated.get("patch") or {}
    preview = generated.get("preview") or {}
    if generated.get("status") != "generated" or (preview.get("validation_report") or {}).get("status") != "valid":
        raise RuntimeError(f"{task_id} did not produce a valid packaged proposal")
    changed_ids = sorted(str(item["event_id"]) for item in (preview.get("diff") or {}).get("changed", []))
    expected_ids = sorted(
        str(item["event_id"])
        for item in task["expected_constraints"]
        if item.get("type") == "voice_equals"
    )
    if changed_ids != expected_ids:
        raise RuntimeError(f"{task_id} preview targeted {changed_ids}, expected {expected_ids}")

    applied = _request(base_url, "/sera-edit/apply", {"score_document": source_score, "patch": patch})
    if not applied.get("committed"):
        raise RuntimeError(f"{task_id} transaction did not commit: {applied.get('rollback_reason')}")
    exported = _request(
        base_url,
        f"/integrations/notation-sessions/{session_id}/export",
        {"score_document": applied["score_document"], "expected_revision": 0},
    )
    host_score = musicxml_to_score_document(exported["musicxml"], source="packaged_voice_roundtrip")
    valid, errors = evaluate_constraints(source_score, host_score, task["expected_constraints"])
    canonical_diff = score_diff(source_score, host_score)
    raw_lanes = _raw_lanes_by_measure(exported["musicxml"])
    fields = {field for item in canonical_diff["changed"] for field in item["changed_fields"]}
    if (
        not valid
        or errors
        or raw_lanes != expected_lanes
        or fields != {"voice"}
        or sorted(item["event_id"] for item in canonical_diff["changed"]) != expected_ids
        or canonical_diff["added"]
        or canonical_diff["deleted"]
        or canonical_diff["global_changes"]
    ):
        raise RuntimeError(
            f"{task_id} packaged voice round-trip mismatch: "
            f"lanes={raw_lanes}, fields={fields}, errors={errors}"
        )
    return {
        "task_id": task_id,
        "session_id": session_id,
        "revision": exported["revision"],
        "changed_event_ids": expected_ids,
        "changed_fields": sorted(fields),
        "raw_lanes_by_measure": raw_lanes,
        "constraint_errors": errors,
    }


def verify(base_url: str) -> dict[str, Any]:
    results = [
        _verify_task(
            base_url,
            "voice_010",
            {1: [[1, 1], [2, 5]], 2: [[1, 1], [2, 5]], 3: [[1, 2], [2, 5]]},
        ),
        _verify_task(
            base_url,
            "voice_004",
            {
                1: [[1, 1], [2, 5], [2, 6]],
                2: [[1, 1], [2, 5], [2, 6]],
                3: [[1, 2], [2, 5], [2, 6]],
            },
        ),
    ]
    return {"passed": True, "tasks": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    print(json.dumps(verify(args.base_url), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

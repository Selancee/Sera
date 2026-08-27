#!/usr/bin/env python3
"""Verify frozen-backend host selection localization through public HTTP APIs."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any


def _request_json(base_url: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body if body is not None else b"",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # Local package verification must not inherit a corporate/user HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def verify(base_url: str) -> dict[str, Any]:
    artifact = _request_json(base_url, "/sera-edit/review/tasks/compound_001/artifacts/source")
    source_path = Path(str(artifact.get("path") or ""))
    if not artifact.get("prepared") or not source_path.is_file():
        raise RuntimeError("Frozen compound_001 source artifact was not prepared.")
    imported = _request_json(
        base_url,
        "/score/import_musicxml",
        {"musicxml": source_path.read_text(encoding="utf-8"), "prompt": "packaged scope regression"},
    )
    preview = _request_json(
        base_url,
        "/sera-edit/generate-preview",
        {
            "score_document": imported["score_document"],
            "instruction": (
                "Transpose the final two notes of measure 2 staff 1 up a semitone "
                "and mark the final note forte."
            ),
            "target_scope": {"measures": [2, 3], "staffs": [1]},
            "protected_scope": {"staffs": [2]},
        },
    )
    changed_ids = sorted(str(item.get("event_id") or "") for item in preview["preview"]["diff"]["changed"])
    expected_ids = ["s007_m2_rh_3", "s007_m2_rh_4"]
    target_measures = list(preview["patch"]["target_scope"]["measures"])
    excluded_measures = list(preview["patch"]["provenance"]["excluded_host_scope"]["measures"])
    validation_status = str(preview["preview"]["validation_report"]["status"])
    passed = (
        preview.get("status") == "generated"
        and validation_status == "valid"
        and target_measures == [2]
        and excluded_measures == [3]
        and changed_ids == expected_ids
    )
    result = {
        "passed": passed,
        "generation_status": preview.get("status"),
        "validation_status": validation_status,
        "host_measures": [2, 3],
        "effective_measures": target_measures,
        "excluded_host_measures": excluded_measures,
        "changed_event_ids": changed_ids,
        "measure_3_changed": any(event_id.startswith("s007_m3_") for event_id in changed_ids),
        "scope_resolution": preview["patch"]["provenance"].get("scope_resolution"),
    }
    if not passed:
        raise RuntimeError(f"Frozen host-scope regression failed: {json.dumps(result, ensure_ascii=False)}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.base_url), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

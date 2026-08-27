"""Create a compact, auditable publication snapshot of a runtime acceptance run."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPRESENTATIVE_TASKS = (
    "pitch_001",
    "rhythm_001",
    "key_001",
    "voice_001",
    "dynamics_001",
    "insertion_001",
    "ties_001",
    "meter_001",
    "compound_001",
    "conflict_001",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def export_runtime_evidence(source: Path, output: Path) -> dict[str, Any]:
    """Copy compact results plus hashes and representative raw evidence."""

    source = source.resolve()
    output = output.resolve()
    summary = _read_json(source / "summary.json")
    results = summary.get("results") or {}
    if int(results.get("failed", -1)) != 0 or int(results.get("passed", 0)) != int(results.get("tasks", -1)):
        raise ValueError("source runtime acceptance run is incomplete or contains failures")
    reproducibility = results.get("reproducibility") or {}
    if reproducibility.get("repeated_task_language_groups") and reproducibility.get("rate") != 1.0:
        raise ValueError("source runtime acceptance repetitions are not fingerprint-identical")

    output.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "summary.json", "metrics.csv", "failures.csv"):
        _copy(source / name, output / name)

    raw_files = sorted((source / "raw_outputs").glob("*.json"))
    host_files = sorted((source / "host_outputs").glob("*.musicxml"))
    all_evidence = [*raw_files, *host_files]
    entries = [
        {
            "path": str(path.relative_to(source)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in all_evidence
    ]
    representative: list[str] = []
    for task_id in REPRESENTATIVE_TASKS:
        for language in ("en", "zh"):
            raw = source / "raw_outputs" / f"{task_id}__{language}__r1.json"
            if not raw.is_file():
                raise FileNotFoundError(f"representative raw output is missing: {raw}")
            raw_target = output / "representative_raw_outputs" / raw.name
            _copy(raw, raw_target)
            representative.append(str(raw_target.relative_to(output)).replace("\\", "/"))
            host = source / "host_outputs" / f"{task_id}__{language}__r1.musicxml"
            if host.is_file():
                host_target = output / "representative_host_outputs" / host.name
                _copy(host, host_target)
                representative.append(str(host_target.relative_to(output)).replace("\\", "/"))

    review_host_outputs: list[dict[str, Any]] = []
    for raw in raw_files:
        raw_payload = _read_json(raw)
        if str((raw_payload.get("generation") or {}).get("status")) == "refused":
            continue
        task_id = str(raw_payload.get("task_id") or "")
        language = str(raw_payload.get("language") or "en")
        repetition = int(raw_payload.get("repetition") or 1)
        if repetition != 1:
            continue
        host = source / "host_outputs" / f"{task_id}__{language}__r1.musicxml"
        if not host.is_file():
            raise FileNotFoundError(f"review host output is missing: {host}")
        target = output / "review_host_outputs" / f"{task_id}__{language}.musicxml"
        _copy(host, target)
        review_host_outputs.append(
            {
                "task_id": task_id,
                "language": language,
                "path": str(target.relative_to(output)).replace("\\", "/"),
                "bytes": target.stat().st_size,
                "sha256": _sha256(target),
            }
        )

    payload = {
        "schema_version": "1.0.0",
        "created_at": datetime.now(UTC).isoformat(),
        "source_experiment_id": summary.get("experiment_id"),
        "evidence_class": summary.get("evidence_class"),
        "paper_model_result_eligible": False,
        "gold_used_for_generation": False,
        "full_evidence_file_count": len(entries),
        "raw_output_count": len(raw_files),
        "host_output_count": len(host_files),
        "full_evidence_files": entries,
        "representative_files": representative,
        "review_host_output_count": len(review_host_outputs),
        "review_host_outputs": review_host_outputs,
        "boundary": (
            "This snapshot is deterministic product acceptance evidence. It does not measure remote LLM accuracy "
            "and does not replace blinded human musical review."
        ),
    }
    manifest_path = output / "evidence_manifest.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "experiments" / "runtime_acceptance_core_bilingual_r3_v4_20260826",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "experiments" / "softwarex_runtime_acceptance_720_v4",
    )
    args = parser.parse_args()
    payload = export_runtime_evidence(args.source, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "source_experiment_id": payload["source_experiment_id"],
                "evidence_files_hashed": payload["full_evidence_file_count"],
                "representative_files_copied": len(payload["representative_files"]),
                "review_host_outputs_copied": payload["review_host_output_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

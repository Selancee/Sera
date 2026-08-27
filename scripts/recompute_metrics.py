"""Recompute deterministic SeraEdit metrics from saved normalized outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.score_document_service import normalize_score_document
from evaluation.benchmark_io import load_task
from evaluation.conditions.sera_edit_conditions import ConditionOutcome
from evaluation.metrics.sera_edit_metrics import compute_task_metrics
from sera_edit.providers.base import ProviderResponse


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _restore_outcome(payload: dict[str, Any]) -> ConditionOutcome:
    restored = dict(payload)
    restored["provider_response"] = ProviderResponse(**restored["provider_response"])
    restored["repair_responses"] = [ProviderResponse(**item) for item in restored.get("repair_responses") or []]
    return ConditionOutcome(**restored)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = set().union(*(row.keys() for row in rows)) if rows else set()
    preferred = ["run_id", "task_id", "category", "condition", "provider", "model", "repetition", "result_class"]
    fieldnames = [field for field in preferred if field in fields] + sorted(fields.difference(preferred))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def recompute(experiment_dir: Path, output: Path) -> dict[str, Any]:
    """Recreate metric rows without consulting a model or modifying raw evidence."""

    manifest = _load_json(experiment_dir / "manifest.json")
    benchmark_root = ROOT / "benchmark"
    rows: list[dict[str, Any]] = []
    for line in (experiment_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        run = json.loads(line)
        task = load_task(benchmark_root, run["task_id"], manifest["split"])
        source = normalize_score_document(_load_json(benchmark_root / "source_scores" / f"{task['score_id']}.score.json"))
        expected = (
            normalize_score_document(_load_json(benchmark_root / task["expected_output_path"]))
            if task.get("expected_output_path")
            else None
        )
        normalized = _load_json(ROOT / run["normalized_output_path"])
        outcome = _restore_outcome(normalized)
        metrics = compute_task_metrics(task, source, outcome, expected)
        metrics.update(
            {
                "run_id": run["run_id"],
                "repetition": run["repetition"],
                "provider": run["provider"],
                "model": run["model"],
                "result_class": run["result_class"],
            }
        )
        rows.append(metrics)
    rows.sort(key=lambda item: item["run_id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output, rows)
    report = {
        "experiment_id": manifest["experiment_id"],
        "source": str((experiment_dir / "runs.jsonl").relative_to(ROOT)).replace("\\", "/"),
        "output": str(output.relative_to(ROOT)).replace("\\", "/"),
        "rows": len(rows),
        "provider_calls": 0,
        "note": "Metrics were deterministically recomputed from saved normalized outputs.",
    }
    (experiment_dir / "recompute_manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Experiment ID under experiments/")
    parser.add_argument("--output", help="Output CSV; defaults to metrics_recomputed.csv in the experiment")
    args = parser.parse_args()
    experiment_dir = ROOT / "experiments" / args.experiment
    output = Path(args.output).resolve() if args.output else experiment_dir / "metrics_recomputed.csv"
    print(json.dumps(recompute(experiment_dir, output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

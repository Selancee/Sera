"""Resumable, cached, budgeted, evidence-preserving SeraEdit experiment runner."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

import yaml

from backend.services.score_document_service import normalize_score_document
from evaluation.benchmark_io import load_task, resolve_task_path
from evaluation.conditions.sera_edit_conditions import ConditionOutcome, run_condition
from evaluation.metrics.sera_edit_metrics import compute_task_metrics
from evaluation.runners.runtime_controls import BudgetExceeded, BudgetLedger, ControlledProvider
from sera_edit.generation.prompts import build_condition_messages, prompt_metadata
from sera_edit.providers.factory import create_provider


ROOT = Path(__file__).resolve().parents[2]
VALID_CONDITIONS = {"full_rewrite", "patch_only", "sera_full"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _git_metadata() -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True, timeout=5
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True, timeout=10
            ).stdout.strip()
        )
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def _dependency_hash() -> str:
    digest = hashlib.sha256()
    for name in ("pyproject.toml", "requirements.txt", "frontend/package-lock.json"):
        path = ROOT / name
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _benchmark_hash(benchmark_root: Path, split: dict[str, Any], split_name: str) -> str:
    """Hash every benchmark input that can change an experiment result."""

    digest = hashlib.sha256()
    digest.update(json.dumps(split, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    seen: set[Path] = set()
    for task_id in split["task_ids"]:
        task_path = resolve_task_path(benchmark_root, task_id, split_name)
        task = _load_json(task_path)
        paths = [task_path, benchmark_root / "source_scores" / f"{task['score_id']}.score.json"]
        for field in ("gold_patch_path", "expected_output_path"):
            if task.get(field):
                paths.append(benchmark_root / str(task[field]))
        for path in paths:
            resolved = path.resolve()
            if resolved in seen:
                continue
            digest.update(str(path.relative_to(benchmark_root)).replace("\\", "/").encode("utf-8"))
            digest.update(path.read_bytes())
            seen.add(resolved)
    return digest.hexdigest()


def _config_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _provider_configs(config: dict[str, Any]) -> list[dict[str, Any]]:
    providers = config.get("providers")
    if providers is None:
        providers = [config.get("provider")]
    if not isinstance(providers, list) or not providers or any(not isinstance(item, dict) for item in providers):
        raise ValueError("config must define provider: {...} or providers: [{...}]")
    return [dict(item) for item in providers]


def _validate_config(config: dict[str, Any]) -> None:
    conditions = config.get("conditions")
    if not isinstance(conditions, list) or not conditions or any(item not in VALID_CONDITIONS for item in conditions):
        raise ValueError(f"conditions must be a non-empty subset of {sorted(VALID_CONDITIONS)}")
    if int(config.get("repetitions", 1)) < 1:
        raise ValueError("repetitions must be at least 1")
    if int(config.get("max_concurrency", 1)) < 1:
        raise ValueError("max_concurrency must be at least 1")
    if int(config.get("max_retries", 0)) < 0:
        raise ValueError("max_retries cannot be negative")
    if int(config.get("max_repair_attempts", 2)) < 0:
        raise ValueError("max_repair_attempts cannot be negative")
    provider_configs = _provider_configs(config)
    formal = bool(config.get("formal_results_allowed", False))
    for provider in provider_configs:
        if "api_key" in provider:
            raise ValueError("inline api_key is forbidden; use api_key_env")
        if provider.get("provider") == "mock" and formal:
            raise ValueError("mock experiments must set formal_results_allowed=false")
        if provider.get("provider") != "mock" and formal:
            if provider.get("input_cost_per_million") is None or provider.get("output_cost_per_million") is None:
                raise ValueError("formal live runs require configured input/output prices for cost accounting")
            if float(config.get("budget_limit_usd", 0)) <= 0:
                raise ValueError("formal live runs require a positive budget_limit_usd")


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _failure_metrics(task: dict[str, Any], condition: str, error: str) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "category": task["category"],
        "condition": condition,
        "expected_status": task["expected_status"],
        "refused": 0,
        "output_produced": 0,
        "musicxml_validity": 0,
        "patch_parse": "",
        "task_success": 0,
        "non_target_preservation": 0.0,
        "complete_preservation": 0,
        "operation_minimality": 0.0,
        "element_change_precision": 0.0,
        "constraints_satisfied": 0,
        "constraint_total": max(1, len(task["expected_constraints"])),
        "constraint_satisfaction": 0.0,
        "correct_refusal": 0,
        "unsafe_execution": 0,
        "repair_attempted": 0,
        "repair_success": 0,
        "repair_attempt_count": 0,
        "repair_added_cost": 0.0,
        "provider_latency_ms": 0.0,
        "processing_latency_ms": 0.0,
        "latency_ms": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost": 0.0,
        "error_codes": "E20",
        "error": error,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], preferred: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = set().union(*(row.keys() for row in rows)) if rows else set(preferred or [])
    fieldnames = [name for name in (preferred or []) if name in fields]
    fieldnames.extend(sorted(fields - set(fieldnames)))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _summary_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"runs": 0}
    latencies = [float(row.get("latency_ms") or 0) for row in rows]
    return {
        "runs": len(rows),
        "musicxml_validity": mean(float(row["musicxml_validity"]) for row in rows if row["musicxml_validity"] != "") if any(row["musicxml_validity"] != "" for row in rows) else None,
        "patch_parse_rate": mean(float(row["patch_parse"]) for row in rows if row["patch_parse"] != "") if any(row["patch_parse"] != "" for row in rows) else None,
        "task_success": mean(float(row["task_success"]) for row in rows),
        "non_target_preservation": mean(float(row["non_target_preservation"]) for row in rows),
        "operation_minimality": mean(float(row["operation_minimality"]) for row in rows),
        "constraint_satisfaction": mean(float(row["constraint_satisfaction"]) for row in rows),
        "median_latency_ms": median(latencies),
        "mean_latency_ms": mean(latencies),
        "p90_latency_ms": _percentile(latencies, 0.90),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "input_tokens": sum(int(row.get("input_tokens") or 0) for row in rows),
        "output_tokens": sum(int(row.get("output_tokens") or 0) for row in rows),
        "estimated_cost": sum(float(row.get("estimated_cost") or 0) for row in rows),
        "repair_attempts": sum(int(row.get("repair_attempt_count") or 0) for row in rows),
        "repair_successes": sum(int(row.get("repair_success") or 0) for row in rows),
        "repair_added_cost": sum(float(row.get("repair_added_cost") or 0) for row in rows),
    }


def run_experiment(config_path: Path, *, experiment_id: str | None = None) -> dict[str, Any]:
    """Run or resume one configured experiment with bounded provider controls."""

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("experiment config must be a YAML object")
    _validate_config(config)
    actual_id = experiment_id or str(config["experiment_id"])
    experiment_dir = ROOT / "experiments" / actual_id
    experiment_dir.mkdir(parents=True, exist_ok=True)
    benchmark_root = (ROOT / config.get("benchmark_root", "benchmark")).resolve()
    split = _load_json(benchmark_root / "splits" / f"{config['split']}.json")
    benchmark_hash = _benchmark_hash(benchmark_root, split, str(config["split"]))
    provider_configs = _provider_configs(config)
    formal = bool(config.get("formal_results_allowed", False))
    result_class = "formal_live" if formal else ("mock_non_formal" if all(item.get("provider") == "mock" for item in provider_configs) else "live_non_formal")
    config_snapshot = experiment_dir / "config_snapshot.yaml"
    if config_snapshot.exists() and config_snapshot.read_bytes() != config_path.read_bytes():
        raise ValueError(f"experiment {actual_id} already exists with a different config snapshot")
    if not config_snapshot.exists():
        shutil.copyfile(config_path, config_snapshot)

    providers: list[tuple[dict[str, Any], ControlledProvider, BudgetLedger]] = []
    total_budget = config.get("budget_limit_usd")
    per_provider_budget = (
        None if total_budget is None else float(total_budget) / max(1, len(provider_configs))
    )
    for provider_config in provider_configs:
        inner = create_provider(provider_config, benchmark_root)
        costs = (
            provider_config.get("input_cost_per_million"),
            provider_config.get("output_cost_per_million"),
        )
        ledger = BudgetLedger(per_provider_budget, *costs)
        controlled = ControlledProvider(
            inner,
            cache_root=ROOT / "experiments" / "_cache",
            cache_enabled=bool(config.get("cache", True)),
            max_retries=int(config.get("max_retries", 0)),
            retry_backoff_seconds=float(config.get("retry_backoff_seconds", 1.0)),
            requests_per_minute=provider_config.get("requests_per_minute"),
            budget=ledger,
        )
        providers.append((provider_config, controlled, ledger))

    prompt_info = {condition: prompt_metadata(condition) for condition in config["conditions"]}
    if "sera_full" in config["conditions"]:
        prompt_info["sera_repair"] = prompt_metadata("sera_repair")
    manifest_path = experiment_dir / "manifest.json"
    if manifest_path.exists():
        manifest = _load_json(manifest_path)
        if (
            manifest.get("config_hash") != _config_hash(config)
            or manifest.get("prompt_metadata") != prompt_info
            or manifest.get("benchmark_hash") != benchmark_hash
        ):
            raise ValueError(f"experiment {actual_id} cannot resume after config, prompt, or benchmark drift")
    else:
        manifest = {
            "experiment_id": actual_id,
            "created_at": datetime.now(UTC).isoformat(),
            "result_class": result_class,
            "formal_results_allowed": formal,
            "split": config["split"],
            "task_count": len(split["task_ids"]),
            "conditions": config["conditions"],
            "repetitions": int(config.get("repetitions", 1)),
            "providers": [
                {key: value for key, value in item.items() if key not in {"api_key", "api_key_value"}}
                for item in provider_configs
            ],
            "prompt_metadata": prompt_info,
            "config_hash": _config_hash(config),
            "benchmark_hash": benchmark_hash,
            "git": _git_metadata(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "dependency_lock_hash": _dependency_hash(),
        }
        _write_json(manifest_path, manifest)

    runs_path = experiment_dir / "runs.jsonl"
    completed: set[str] = set()
    existing_rows: list[dict[str, Any]] = []
    if runs_path.exists():
        for line in runs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                completed.add(row["run_id"])
                existing_rows.append(row)

    multiple_providers = len(providers) > 1
    jobs: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any] | None, str, int, ControlledProvider]] = []
    for task_id in split["task_ids"]:
        task = load_task(benchmark_root, task_id, config["split"])
        source = normalize_score_document(_load_json(benchmark_root / "source_scores" / f"{task['score_id']}.score.json"))
        expected = normalize_score_document(_load_json(benchmark_root / task["expected_output_path"])) if task["expected_output_path"] else None
        for _, provider, _ in providers:
            provider_slug = f":{provider.provider}:{provider.model}" if multiple_providers else ""
            for condition in config["conditions"]:
                for repetition in range(1, int(config.get("repetitions", 1)) + 1):
                    run_id = f"{task_id}:{condition}{provider_slug}:r{repetition}"
                    if run_id not in completed:
                        jobs.append((run_id, task, source, expected, condition, repetition, provider))

    def execute(job: tuple[str, dict[str, Any], dict[str, Any], dict[str, Any] | None, str, int, ControlledProvider]) -> dict[str, Any]:
        run_id, task, source, expected, condition, repetition, provider = job
        try:
            outcome = run_condition(
                condition,
                task,
                source,
                provider,
                temperature=float(config.get("temperature", 0.0)),
                seed=None if config.get("seed") is None else int(config["seed"]) + repetition - 1,
                max_tokens=config.get("max_tokens"),
                max_repair_attempts=int(config.get("max_repair_attempts", 2)),
            )
            metrics = compute_task_metrics(task, source, outcome, expected)
            error = outcome.error
            error_codes = metrics["error_codes"]
            response = outcome.provider_response.as_dict()
            response["repair_responses"] = [item.as_dict() for item in outcome.repair_responses]
            normalized = outcome.as_dict()
        except BudgetExceeded:
            raise
        except Exception as exc:  # noqa: BLE001 - experiment failures must be serialized per task.
            metrics = _failure_metrics(task, condition, str(exc))
            error = str(exc)
            error_codes = "E20"
            response = {"error": str(exc), "exception_type": type(exc).__name__}
            normalized = {"condition": condition, "error": str(exc), "error_codes": ["E20"]}
        metrics.update(
            {
                "run_id": run_id,
                "repetition": repetition,
                "provider": provider.provider,
                "model": provider.model,
                "result_class": result_class,
            }
        )
        output_slug = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:12]
        raw_path = experiment_dir / "raw_outputs" / f"{task['task_id']}__{condition}__r{repetition}__{output_slug}.json"
        normalized_path = experiment_dir / "normalized_outputs" / f"{task['task_id']}__{condition}__r{repetition}__{output_slug}.json"
        messages, response_schema = build_condition_messages(condition, task, source)
        _write_json(
            raw_path,
            {
                "run_id": run_id,
                "request": {
                    "messages": messages,
                    "response_schema_hash": hashlib.sha256(json.dumps(response_schema, sort_keys=True).encode("utf-8")).hexdigest() if response_schema else None,
                    "temperature": config.get("temperature", 0.0),
                    "seed": config.get("seed"),
                    "max_tokens": config.get("max_tokens"),
                },
                "response": response,
            },
        )
        _write_json(normalized_path, normalized)
        return {
            "run_id": run_id,
            "task_id": task["task_id"],
            "condition": condition,
            "repetition": repetition,
            "provider": provider.provider,
            "model": provider.model,
            "result_class": result_class,
            "metrics": metrics,
            "raw_output_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "normalized_output_path": str(normalized_path.relative_to(ROOT)).replace("\\", "/"),
            "error": error,
            "error_codes": error_codes,
        }

    new_rows: list[dict[str, Any]] = []
    budget_errors: list[dict[str, Any]] = []
    interrupted = False
    executor = ThreadPoolExecutor(max_workers=int(config.get("max_concurrency", 1)), thread_name_prefix="seraedit-eval")
    futures: dict[Future[dict[str, Any]], tuple[Any, ...]] = {executor.submit(execute, job): job for job in jobs}
    try:
        for future in as_completed(futures):
            job = futures[future]
            try:
                row = future.result()
            except BudgetExceeded as exc:
                budget_errors.append({"run_id": job[0], "task_id": job[1]["task_id"], "condition": job[4], "error": str(exc), "error_codes": "BUDGET_EXHAUSTED"})
                continue
            with runs_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
            new_rows.append(row)
    except KeyboardInterrupt:
        interrupted = True
        for future in futures:
            future.cancel()
    finally:
        executor.shutdown(wait=not interrupted, cancel_futures=interrupted)

    all_rows = [*existing_rows, *new_rows]
    metrics_rows = []
    for row in all_rows:
        metrics = dict(row["metrics"])
        for field in ("run_id", "provider", "model", "repetition", "result_class"):
            metrics.setdefault(field, row.get(field))
        metrics_rows.append(metrics)
    run_errors = [
        {
            "run_id": row["run_id"],
            "task_id": row["task_id"],
            "condition": row["condition"],
            "provider": row.get("provider"),
            "model": row.get("model"),
            "error": row.get("error"),
            "error_codes": row.get("error_codes") or row.get("metrics", {}).get("error_codes"),
        }
        for row in all_rows
        if row.get("error")
    ]
    _write_csv(experiment_dir / "metrics.csv", metrics_rows, preferred=["run_id", "task_id", "category", "condition", "provider", "model", "repetition", "result_class"])
    _write_csv(experiment_dir / "errors.csv", [*run_errors, *budget_errors], preferred=["run_id", "task_id", "condition", "provider", "model", "error_codes", "error"])
    expected_runs = len(split["task_ids"]) * len(config["conditions"]) * int(config.get("repetitions", 1)) * len(providers)
    provider_summaries: dict[str, Any] = {}
    for _, provider, ledger in providers:
        key = f"{provider.provider}:{provider.model}"
        provider_rows = [row for row in metrics_rows if row.get("provider") == provider.provider and row.get("model") == provider.model]
        provider_summaries[key] = {
            "conditions": {
                condition: _summary_group([row for row in provider_rows if row["condition"] == condition])
                for condition in config["conditions"]
            },
            "budget_spent_or_reserved_usd": ledger.spent_usd + ledger.reserved_usd,
        }
    summary = {
        "experiment_id": actual_id,
        "result_class": result_class,
        "formal_results_allowed": formal,
        "completed_runs": len(metrics_rows),
        "expected_runs": expected_runs,
        "new_runs": len(new_rows),
        "error_count": len(run_errors),
        "budget_blocked_count": len(budget_errors),
        "budget_limit_usd": total_budget,
        "budget_spent_or_reserved_usd": sum(ledger.spent_usd + ledger.reserved_usd for _, _, ledger in providers),
        "interrupted": interrupted,
        "providers": provider_summaries,
        "warning": "Mock fixture results validate plumbing only and must not be reported as model performance." if result_class == "mock_non_formal" else None,
    }
    if len(provider_summaries) == 1:
        summary["conditions"] = next(iter(provider_summaries.values()))["conditions"]
    _write_json(experiment_dir / "summary.json", summary)
    return summary

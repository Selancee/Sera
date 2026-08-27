"""Replay benchmark instructions through the interactive Sera product pipeline.

This runner is deliberately separate from the three-condition model experiment.
It answers a different question: can the product turn each benchmark instruction
into a validated patch, commit it atomically, and round-trip the resulting
MusicXML without consulting the Gold patch as a generator input?
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any, Literal

from backend.services.musicxml_source_patch_service import patch_musicxml_preserving_source
from backend.services.score_document_service import musicxml_to_score_document, normalize_score_document
from backend.validation.musicxml_validator import MusicXMLValidator
from evaluation.benchmark_io import load_task, resolve_task_path
from evaluation.conditions.sera_edit_conditions import ConditionOutcome
from evaluation.metrics.sera_edit_metrics import compute_task_metrics
from scripts.validate_benchmark import evaluate_constraints
from sera_edit.execution.transaction import PatchTransaction
from sera_edit.domain.score_scope import ScoreScope
from sera_edit.generation.instruction_scope import explicit_instruction_measures
from sera_edit.generation.llm_patch_generator import generate_patch_with_runtime
from sera_edit.providers.base import ProviderResponse
from sera_edit.providers.runtime import LLMRuntimeSettings, runtime_settings


ROOT = Path(__file__).resolve().parents[2]
AcceptanceMode = Literal["local", "configured"]
InstructionLanguage = Literal["en", "zh"]
HostScopeMode = Literal["exact", "expanded_adjacent"]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _local_settings() -> LLMRuntimeSettings:
    """Return an explicit no-network runtime for repeatable product acceptance."""

    return LLMRuntimeSettings(
        provider="local_rule",
        model="seraedit_rule_v1",
        base_url="",
        api_key_env="",
        configured=False,
        available=False,
        transport="local",
        fallback_local=True,
        timeout_seconds=90.0,
        max_output_tokens=4000,
        reasoning_effort="low",
        store=False,
        supports_structured_outputs=False,
        input_cost_per_million=None,
        output_cost_per_million=None,
        config_file="",
        reason="Explicit offline runtime acceptance mode.",
    )


def _benchmark_hash(benchmark_root: Path, split_name: str, task_ids: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update(split_name.encode("utf-8"))
    digest.update(json.dumps(task_ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    seen: set[Path] = set()
    for task_id in task_ids:
        task_path = resolve_task_path(benchmark_root, task_id, split_name)
        task = _read_json(task_path)
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
    return f"sha256:{digest.hexdigest()}"


def _provider_response(generation: dict[str, Any], elapsed_ms: float) -> ProviderResponse:
    generator = generation.get("generator") or {}
    return ProviderResponse(
        raw_text=json.dumps(generation.get("patch") or {"status": generation.get("status")}, ensure_ascii=False),
        parsed_output=generation.get("patch"),
        provider=str(generator.get("provider") or "local_rule"),
        model=str(generator.get("model") or "seraedit_rule_v1"),
        latency_ms=float(generator.get("latency_ms") or 0.0),
        input_tokens=generator.get("input_tokens"),
        output_tokens=generator.get("output_tokens"),
        estimated_cost=generator.get("estimated_cost"),
        request_id=generator.get("request_id"),
        finish_reason="completed" if generation.get("status") in {"generated", "refused"} else "unsupported",
        error=None if generation.get("status") in {"generated", "refused"} else str(generation.get("reason") or "unsupported"),
    )


def _host_target_scope(
    task_target_scope: dict[str, Any],
    instruction: str,
    score_document: dict[str, Any],
    mode: HostScopeMode,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the host-facing scope and auditable perturbation metadata."""

    original = ScoreScope.from_dict(task_target_scope)
    metadata: dict[str, Any] = {
        "mode": mode,
        "applied": False,
        "extra_measures": [],
        "reason": "exact benchmark scope",
    }
    if mode == "exact":
        return original.as_dict(), metadata
    explicit_measures = set(explicit_instruction_measures(instruction))
    if not explicit_measures:
        metadata["reason"] = "instruction does not explicitly name a measure"
        return original.as_dict(), metadata
    if original.whole_score:
        metadata["reason"] = "whole-score target is not eligible for adjacent-measure expansion"
        return original.as_dict(), metadata

    available = sorted(int(measure.get("number", 0)) for measure in score_document.get("measures") or [])
    base_measures = set(original.measures) or explicit_measures
    candidates = [number for number in available if number not in base_measures and number not in original.exclude_measures]
    if not candidates:
        metadata["reason"] = "source score has no adjacent unselected measure"
        return original.as_dict(), metadata
    boundary = max(base_measures)
    after = [number for number in candidates if number > boundary]
    before = [number for number in candidates if number < min(base_measures)]
    extra_measure = min(after) if after else max(before)

    payload = original.as_dict()
    payload["measures"] = sorted(base_measures | {extra_measure})
    if original.event_ids:
        adjacent_selector = ScoreScope(
            measures=frozenset({extra_measure}),
            parts=original.parts,
            staffs=original.staffs,
            voices=original.voices,
            exclude_event_ids=original.exclude_event_ids,
            time_range=original.time_range,
        )
        adjacent_ids = {context.event_id for context in adjacent_selector.select(score_document)}
        payload["event_ids"] = sorted(set(original.event_ids) | adjacent_ids)
    metadata.update(
        {
            "applied": True,
            "extra_measures": [extra_measure],
            "reason": "expanded host selection around explicit instruction measure",
        }
    )
    return payload, metadata


def _outcome(
    task: dict[str, Any],
    generation: dict[str, Any],
    transaction: Any | None,
    elapsed_ms: float,
) -> ConditionOutcome:
    refused = generation.get("status") == "refused"
    committed = bool(transaction and transaction.committed)
    errors = [] if refused or committed else [
        item.code for item in (transaction.report.errors if transaction is not None else [])
    ]
    if not refused and not committed and not errors:
        errors = ["E19" if generation.get("status") == "unsupported" else "E20"]
    return ConditionOutcome(
        condition="interactive_runtime_acceptance",
        refusal=refused,
        score_document=transaction.score_document if committed else None,
        musicxml=transaction.musicxml if committed else None,
        patch=generation.get("patch"),
        patch_parsed=generation.get("patch") is not None,
        validation_report=(
            transaction.report.as_dict()
            if transaction is not None
            else {"status": generation.get("status"), "reason": generation.get("reason")}
        ),
        provider_response=_provider_response(generation, elapsed_ms),
        processing_latency_ms=max(0.0, elapsed_ms - float((generation.get("generator") or {}).get("latency_ms") or 0.0)),
        error_codes=errors,
        error=None if refused or committed else str(generation.get("reason") or getattr(transaction, "rollback_reason", None) or "runtime acceptance failed"),
        repair_attempted=int((generation.get("generator") or {}).get("generation_attempts") or 1) > 1,
        repair_success=committed and int((generation.get("generator") or {}).get("generation_attempts") or 1) > 1,
        repair_attempt_count=max(0, int((generation.get("generator") or {}).get("generation_attempts") or 1) - 1),
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted(set().union(*(row.keys() for row in rows))) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def _semantic_patch_fingerprint(patch: dict[str, Any] | None) -> str:
    """Hash executable patch meaning without language-specific prose or patch IDs."""

    if patch is None:
        payload: Any = {"refusal": True}
    else:
        payload = {
            "target_scope": patch.get("target_scope"),
            "protected_scope": patch.get("protected_scope"),
            "operations": [
                {key: value for key, value in operation.items() if key != "operation_id"}
                for operation in (patch.get("operations") or [])
            ],
            "expected_effects": patch.get("expected_effects") or [],
        }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [float(row["latency_ms"]) for row in rows]
    executable_rows = [row for row in rows if row.get("expected_status") == "success"]
    categories: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["category"])].append(row)
    for category, items in sorted(grouped.items()):
        categories[category] = {
            "tasks": len(items),
            "passed": sum(int(item["task_success"]) for item in items),
            "failed": sum(not bool(item["task_success"]) for item in items),
            "pass_rate": mean(float(item["task_success"]) for item in items),
        }
    reproducibility_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        reproducibility_groups[f"{row['task_id']}:{row.get('language', 'en')}"].append(row)
    repeated_groups = [items for items in reproducibility_groups.values() if len(items) > 1]
    reproducible_groups = sum(
        len({item.get("patch_fingerprint") for item in items}) == 1
        and len({item.get("post_fingerprint") for item in items}) == 1
        for items in repeated_groups
    )
    cross_language_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cross_language_groups[str(row["task_id"])].append(row)
    bilingual_groups = [
        items for items in cross_language_groups.values()
        if len({str(item.get("language") or "en") for item in items}) > 1
    ]
    semantic_equivalent_groups = sum(
        len({item.get("semantic_patch_fingerprint") for item in items}) == 1
        for items in bilingual_groups
    )
    output_equivalent_groups = sum(
        len({item.get("post_fingerprint") for item in items}) == 1
        for items in bilingual_groups
    )
    return {
        "tasks": len(rows),
        "passed": sum(int(row["task_success"]) for row in rows),
        "failed": sum(not bool(row["task_success"]) for row in rows),
        "pass_rate": mean(float(row["task_success"]) for row in rows) if rows else 0.0,
        "constraint_satisfaction": mean(float(row["constraint_satisfaction"]) for row in rows) if rows else 0.0,
        "complete_preservation_rate": mean(float(row["complete_preservation"]) for row in rows) if rows else 0.0,
        "musicxml_validity": mean(float(row["musicxml_validity"]) for row in rows if row["musicxml_validity"] != "") if any(row["musicxml_validity"] != "" for row in rows) else None,
        "correct_refusals": sum(int(row["correct_refusal"]) for row in rows),
        "unsafe_executions": sum(int(row["unsafe_execution"]) for row in rows),
        "source_preserving_host_export": {
            "expected": len(executable_rows),
            "succeeded": sum(int(row.get("host_export_valid") or 0) for row in executable_rows),
            "failed": sum(not bool(row.get("host_export_valid")) for row in executable_rows),
            "rate": mean(float(row.get("host_export_valid") or 0) for row in executable_rows)
            if executable_rows
            else None,
        },
        "median_latency_ms": median(latencies) if latencies else 0.0,
        "p95_latency_ms": _percentile(latencies, 0.95),
        "generation_statuses": dict(Counter(str(row["generation_status"]) for row in rows)),
        "reproducibility": {
            "repeated_task_language_groups": len(repeated_groups),
            "identical_patch_and_output_groups": reproducible_groups,
            "rate": reproducible_groups / max(1, len(repeated_groups)) if repeated_groups else None,
        },
        "cross_language_equivalence": {
            "task_groups": len(bilingual_groups),
            "semantic_patch_equivalent_groups": semantic_equivalent_groups,
            "output_equivalent_groups": output_equivalent_groups,
            "semantic_patch_rate": semantic_equivalent_groups / max(1, len(bilingual_groups)) if bilingual_groups else None,
            "output_rate": output_equivalent_groups / max(1, len(bilingual_groups)) if bilingual_groups else None,
        },
        "categories": categories,
    }


def run_runtime_acceptance(
    *,
    benchmark_root: Path = ROOT / "benchmark",
    split_name: str = "core",
    experiment_dir: Path,
    mode: AcceptanceMode = "local",
    task_ids: list[str] | None = None,
    languages: list[InstructionLanguage] | None = None,
    repetitions: int = 1,
    host_scope_mode: HostScopeMode = "exact",
    latest_report_path: Path | None = None,
) -> dict[str, Any]:
    """Run or resume product-level acceptance without using Gold as generation input."""

    benchmark_root = benchmark_root.resolve()
    split = _read_json(benchmark_root / "splits" / f"{split_name}.json")
    selected_ids = list(task_ids or split["task_ids"])
    selected_languages = list(dict.fromkeys(languages or ["en"]))
    if not selected_languages or any(language not in {"en", "zh"} for language in selected_languages):
        raise ValueError("languages must be a non-empty subset of en and zh")
    unknown = sorted(set(selected_ids) - set(split["task_ids"]))
    if unknown:
        raise ValueError(f"tasks are not members of split {split_name}: {unknown}")
    if mode not in {"local", "configured"}:
        raise ValueError("mode must be local or configured")
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    if host_scope_mode not in {"exact", "expanded_adjacent"}:
        raise ValueError("host_scope_mode must be exact or expanded_adjacent")
    settings = _local_settings() if mode == "local" else runtime_settings()
    benchmark_hash = _benchmark_hash(benchmark_root, split_name, selected_ids)
    experiment_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = experiment_dir / "manifest.json"
    manifest = {
        "schema_version": "1.0.0",
        "evidence_class": "product_runtime_acceptance_non_formal",
        "paper_model_result_eligible": False,
        "gold_used_for_generation": False,
        "gold_used_for_deterministic_evaluation_only": True,
        "split": split_name,
        "task_ids": selected_ids,
        "task_count": len(selected_ids),
        "languages": selected_languages,
        "repetitions": repetitions,
        "run_count": len(selected_ids) * len(selected_languages) * repetitions,
        "mode": mode,
        "host_scope_mode": host_scope_mode,
        "benchmark_hash": benchmark_hash,
        "runtime_settings": {
            key: value
            for key, value in asdict(settings).items()
            if key not in {"api_key_env", "config_file"}
        },
        "python_version": sys.version,
        "platform": platform.platform(),
    }
    if manifest_path.exists():
        previous = _read_json(manifest_path)
        comparable_keys = {"split", "task_ids", "mode", "host_scope_mode", "benchmark_hash"}
        if (
            any(previous.get(key) != manifest.get(key) for key in comparable_keys)
            or previous.get("languages", ["en"]) != selected_languages
            or int(previous.get("repetitions", 1)) != repetitions
        ):
            raise ValueError("runtime acceptance experiment cannot resume after benchmark or mode drift")
        manifest["created_at"] = previous.get("created_at")
    else:
        manifest["created_at"] = datetime.now(UTC).isoformat()
        _write_json(manifest_path, manifest)

    runs_path = experiment_dir / "runs.jsonl"
    existing: dict[str, dict[str, Any]] = {}
    if runs_path.exists():
        for line in runs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                language = str(row.get("language") or "en")
                repetition = int(row.get("repetition") or 1)
                run_id = str(row.get("run_id") or f"{row['task_id']}:{language}:r{repetition}")
                if run_id.count(":") == 1:
                    run_id = f"{run_id}:r{repetition}"
                existing[run_id] = row

    for task_id in selected_ids:
        task = load_task(benchmark_root, task_id, split_name)
        source_musicxml = (benchmark_root / "source_scores" / f"{task['score_id']}.musicxml").read_text(
            encoding="utf-8"
        )
        source = musicxml_to_score_document(
            source_musicxml,
            source="runtime_acceptance_notation_bridge",
        )
        expected = (
            normalize_score_document(_read_json(benchmark_root / str(task["expected_output_path"])))
            if task.get("expected_output_path")
            else None
        )
        for language in selected_languages:
            for repetition in range(1, repetitions + 1):
                run_id = f"{task_id}:{language}:r{repetition}"
                if run_id in existing:
                    continue
                instruction = str(task.get(f"instruction_{language}") or "")
                host_target_scope, scope_stress = _host_target_scope(
                    dict(task.get("target_scope") or {}),
                    instruction,
                    source,
                    host_scope_mode,
                )
                started = time.perf_counter()
                generation = generate_patch_with_runtime(
                    source,
                    instruction,
                    host_target_scope,
                    dict(task.get("protected_scope") or {}),
                    settings=settings,
                )
                preview = None
                transaction = None
                if generation.get("patch") is not None:
                    preview = PatchTransaction().execute(source, generation["patch"], dry_run=True)
                    transaction = PatchTransaction().execute(source, generation["patch"])
                host_export: dict[str, Any] | None = None
                host_score: dict[str, Any] | None = None
                host_validation: dict[str, Any] | None = None
                host_error: str | None = None
                if transaction is not None and transaction.committed:
                    try:
                        host_export = patch_musicxml_preserving_source(
                            source_musicxml,
                            source,
                            transaction.score_document,
                        )
                        host_validation = MusicXMLValidator().validate_text(
                            str(host_export["musicxml"])
                        ).to_report()
                        if not host_validation.get("valid_musicxml"):
                            raise ValueError(
                                "source-preserving host output failed MusicXML validation: "
                                + str(host_validation.get("errors", []))
                            )
                        host_score = musicxml_to_score_document(
                            str(host_export["musicxml"]),
                            source="runtime_acceptance_host_roundtrip",
                        )
                    except Exception as exc:  # Persisted below as product-path evidence.
                        host_error = str(exc)
                elapsed_ms = (time.perf_counter() - started) * 1000
                outcome = _outcome(task, generation, transaction, elapsed_ms)
                if transaction is not None and transaction.committed:
                    if host_error is not None or host_score is None or host_export is None:
                        outcome.score_document = None
                        outcome.musicxml = None
                        outcome.error_codes = ["E02"]
                        outcome.error = host_error or "source-preserving host export failed"
                    else:
                        outcome.score_document = host_score
                        outcome.musicxml = str(host_export["musicxml"])
                metrics = compute_task_metrics(task, source, outcome, expected)
                constraint_errors: list[str] = []
                if host_score is not None and host_export is not None:
                    _, constraint_errors = evaluate_constraints(
                        source,
                        host_score,
                        task["expected_constraints"],
                    )
                    host_path = experiment_dir / "host_outputs" / f"{task_id}__{language}__r{repetition}.musicxml"
                    host_path.parent.mkdir(parents=True, exist_ok=True)
                    host_path.write_text(str(host_export["musicxml"]), encoding="utf-8")
                raw_path = experiment_dir / "raw_outputs" / f"{task_id}__{language}__r{repetition}.json"
                patch_fingerprint = hashlib.sha256(
                    json.dumps(
                        generation.get("patch"),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                semantic_patch_fingerprint = _semantic_patch_fingerprint(generation.get("patch"))
                post_fingerprint = (
                    hashlib.sha256(str(host_export["musicxml"]).encode("utf-8")).hexdigest()
                    if host_score is not None and host_export is not None
                    else str(transaction.post_fingerprint if transaction is not None else "refused")
                )
                _write_json(
                    raw_path,
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "language": language,
                        "repetition": repetition,
                        "instruction": instruction,
                        "target_scope": task.get("target_scope"),
                        "host_target_scope": host_target_scope,
                        "scope_stress": scope_stress,
                        "protected_scope": task.get("protected_scope"),
                        "generation": generation,
                        "preview": preview.as_dict() if preview is not None else None,
                        "transaction": transaction.as_dict() if transaction is not None else None,
                        "source_preserving_host_export": (
                            {key: value for key, value in host_export.items() if key != "musicxml"}
                            if host_export is not None
                            else None
                        ),
                        "host_validation": host_validation,
                        "host_error": host_error,
                        "constraint_errors": constraint_errors,
                        "elapsed_ms": elapsed_ms,
                        "patch_fingerprint": patch_fingerprint,
                        "semantic_patch_fingerprint": semantic_patch_fingerprint,
                        "post_fingerprint": post_fingerprint,
                    },
                )
                row = metrics | {
                    "run_id": run_id,
                    "task_id": task_id,
                    "language": language,
                    "repetition": repetition,
                    "category": task["category"],
                    "generation_status": generation.get("status"),
                    "generator_provider": (generation.get("generator") or {}).get("provider"),
                    "generator_model": (generation.get("generator") or {}).get("model"),
                    "routing": (generation.get("generator") or {}).get("routing") or (generation.get("generator") or {}).get("transport"),
                    "scope_stress_applied": int(bool(scope_stress["applied"])),
                    "scope_stress_extra_measures": ";".join(str(value) for value in scope_stress["extra_measures"]),
                    "transaction_valid": int(bool(transaction and transaction.committed)),
                    "host_export_valid": int(host_score is not None and host_export is not None),
                    "preview_valid": int(bool(preview and preview.report.status == "valid")),
                    "constraint_errors": "; ".join(constraint_errors),
                    "patch_fingerprint": patch_fingerprint,
                    "semantic_patch_fingerprint": semantic_patch_fingerprint,
                    "post_fingerprint": post_fingerprint,
                    "raw_output_path": str(raw_path.relative_to(ROOT)).replace("\\", "/") if raw_path.is_relative_to(ROOT) else str(raw_path),
                }
                with runs_path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                existing[run_id] = row

    rows = [
        existing[f"{task_id}:{language}:r{repetition}"]
        for task_id in selected_ids
        for language in selected_languages
        for repetition in range(1, repetitions + 1)
    ]
    _write_csv(experiment_dir / "metrics.csv", rows)
    _write_csv(experiment_dir / "failures.csv", [row for row in rows if not bool(row["task_success"])])
    summary = {
        "schema_version": "1.0.0",
        "experiment_id": experiment_dir.name,
        "evidence_class": "product_runtime_acceptance_non_formal",
        "paper_model_result_eligible": False,
        "gold_used_for_generation": False,
        "mode": mode,
        "host_scope_mode": host_scope_mode,
        "languages": selected_languages,
        "repetitions": repetitions,
        "split": split_name,
        "benchmark_hash": benchmark_hash,
        "completed_at": datetime.now(UTC).isoformat(),
        "resumable": True,
        "evidence": {
            "generation_entrypoint": "generate_patch_with_runtime",
            "preview": "PatchTransaction(dry_run=True)",
            "commit": "PatchTransaction(dry_run=False)",
            "host_export": "patch_musicxml_preserving_source",
            "musicxml_roundtrip": "source MusicXML -> source-preserving patch -> host MusicXML -> ScoreDocument",
            "deterministic_constraints": True,
            "per_task_raw_outputs": True,
            "host_openable_outputs": True,
        },
        "results": _summarize(rows)
        | {
            "unique_tasks": len(selected_ids),
            "scope_stress": {
                "mode": host_scope_mode,
                "runs_applied": sum(int(row.get("scope_stress_applied") or 0) for row in rows),
                "runs_passed": sum(
                    int(bool(row.get("task_success")))
                    for row in rows
                    if int(row.get("scope_stress_applied") or 0)
                ),
            },
        },
    }
    _write_json(experiment_dir / "summary.json", summary)
    if latest_report_path is not None:
        experiment_reference = (
            str(experiment_dir.relative_to(ROOT)).replace("\\", "/")
            if experiment_dir.is_relative_to(ROOT)
            else str(experiment_dir)
        )
        _write_json(latest_report_path, summary | {"experiment_dir": experiment_reference})
    return summary

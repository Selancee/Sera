"""Paired tests, bootstrap intervals, effect sizes, and category summaries."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from scipy.stats import binomtest, rankdata, wilcoxon


BINARY_METRICS = ("task_success", "complete_preservation", "correct_refusal", "unsafe_execution")
CONTINUOUS_METRICS = (
    "non_target_preservation",
    "operation_minimality",
    "element_change_precision",
    "constraint_satisfaction",
    "latency_ms",
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(row: dict[str, str], field: str) -> float | None:
    value = row.get(field, "")
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def bootstrap_mean_ci(values: list[float], *, samples: int, seed: int) -> dict[str, float | int | None]:
    """Return a deterministic percentile interval for the sample mean."""

    if not values:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    data = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.choice(data, size=(max(1, samples), len(data)), replace=True).mean(axis=1)
    return {
        "mean": float(data.mean()),
        "ci_low": float(np.quantile(draws, 0.025)),
        "ci_high": float(np.quantile(draws, 0.975)),
        "n": len(values),
    }


def _paired_bootstrap(first: list[float], second: list[float], *, samples: int, seed: int) -> dict[str, float]:
    differences = np.asarray(second, dtype=float) - np.asarray(first, dtype=float)
    if not len(differences):
        return {"mean_difference": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    rng = np.random.default_rng(seed)
    draws = rng.choice(differences, size=(max(1, samples), len(differences)), replace=True).mean(axis=1)
    return {
        "mean_difference": float(differences.mean()),
        "ci_low": float(np.quantile(draws, 0.025)),
        "ci_high": float(np.quantile(draws, 0.975)),
    }


def _mcnemar(first: list[float], second: list[float]) -> dict[str, Any]:
    discordant_first = sum(1 for a, b in zip(first, second, strict=True) if a == 1 and b == 0)
    discordant_second = sum(1 for a, b in zip(first, second, strict=True) if a == 0 and b == 1)
    discordant = discordant_first + discordant_second
    p_value = 1.0 if discordant == 0 else float(
        binomtest(min(discordant_first, discordant_second), discordant, 0.5, alternative="two-sided").pvalue
    )
    return {
        "test": "exact_mcnemar",
        "p_value": p_value,
        "first_only_success": discordant_first,
        "second_only_success": discordant_second,
        "risk_difference": mean(second) - mean(first),
    }


def _paired_rank_test(first: list[float], second: list[float]) -> dict[str, Any]:
    differences = np.asarray(second, dtype=float) - np.asarray(first, dtype=float)
    nonzero = differences[differences != 0]
    if not len(nonzero):
        return {"test": "wilcoxon_signed_rank", "p_value": 1.0, "rank_biserial": 0.0}
    result = wilcoxon(nonzero, zero_method="wilcox", alternative="two-sided", method="auto")
    ranks = rankdata(np.abs(nonzero))
    positive = float(ranks[nonzero > 0].sum())
    negative = float(ranks[nonzero < 0].sum())
    denominator = positive + negative
    return {
        "test": "wilcoxon_signed_rank",
        "p_value": float(result.pvalue),
        "rank_biserial": 0.0 if denominator == 0 else (positive - negative) / denominator,
    }


def _holm_adjust(tests: list[dict[str, Any]]) -> None:
    indexed = sorted(enumerate(tests), key=lambda item: float(item[1]["p_value"]))
    running = 0.0
    total = len(indexed)
    for rank, (index, test) in enumerate(indexed):
        adjusted = min(1.0, (total - rank) * float(test["p_value"]))
        running = max(running, adjusted)
        tests[index]["holm_adjusted_p"] = running


def _pair_rows(rows: list[dict[str, str]], first: str, second: str, metric: str) -> tuple[list[float], list[float]]:
    by_key: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for row in rows:
        value = _number(row, metric)
        if value is None:
            continue
        key = (row["task_id"], row.get("repetition") or "1")
        by_key[key][row["condition"]] = value
    first_values: list[float] = []
    second_values: list[float] = []
    for values in by_key.values():
        if first in values and second in values:
            first_values.append(values[first])
            second_values.append(values[second])
    return first_values, second_values


def _refusal_summary(rows: list[dict[str, str]], condition: str) -> dict[str, Any]:
    selected = [row for row in rows if row["condition"] == condition]
    predicted = [row for row in selected if _number(row, "refused") == 1]
    expected = [row for row in selected if row.get("expected_status") == "refuse"]
    true_positive = sum(1 for row in predicted if row.get("expected_status") == "refuse")
    precision = true_positive / max(1, len(predicted))
    recall = true_positive / max(1, len(expected))
    return {
        "expected_refusals": len(expected),
        "predicted_refusals": len(predicted),
        "true_positive": true_positive,
        "precision": precision,
        "recall": recall,
        "f1": 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall),
        "unsafe_execution_rate": mean([_number(row, "unsafe_execution") or 0.0 for row in expected]) if expected else None,
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [f"# Statistical analysis: {report['experiment_id']}", ""]
    if report["result_class"] != "formal_live":
        lines.extend(
            [
                "> **NON-FORMAL PLACEHOLDER:** this experiment used mock or non-formal outputs. Statistical values validate reporting code only and must not be cited as model performance.",
                "",
            ]
        )
    lines.extend(
        [
            f"- Result class: `{report['result_class']}`",
            f"- Rows: {report['row_count']}",
            f"- Bootstrap samples: {report['bootstrap_samples']}",
            "- Missing values are excluded metric-by-metric before pairing.",
            "- Holm correction is applied across all tests within each provider/model group.",
            "",
        ]
    )
    for group_name, group in report["groups"].items():
        lines.extend([f"## {group_name}", "", "### Descriptive results", ""])
        for condition, metrics in group["descriptive"].items():
            lines.append(f"- `{condition}`: task_success={metrics['task_success']['mean']}, preservation={metrics['non_target_preservation']['mean']}, n={metrics['task_success']['n']}")
        lines.extend(["", "### Paired tests", "", "| Comparison | Metric | Test | N | Difference (second-first) | 95% CI | Holm p | Effect |", "| --- | --- | --- | ---: | ---: | --- | ---: | ---: |"])
        for item in group["paired_tests"]:
            effect = item.get("rank_biserial", item.get("risk_difference", ""))
            lines.append(
                f"| {item['comparison']} | {item['metric']} | {item['test']} | {item['n']} | "
                f"{item['mean_difference']:.4f} | [{item['ci_low']:.4f}, {item['ci_high']:.4f}] | "
                f"{item['holm_adjusted_p']:.4g} | {effect if effect == '' else f'{float(effect):.4f}'} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def analyze_experiment(experiment_dir: Path, *, bootstrap_samples: int = 5000, seed: int = 42) -> dict[str, Any]:
    """Analyze one completed experiment and write JSON/Markdown reports."""

    experiment_dir = experiment_dir.resolve()
    manifest = json.loads((experiment_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = _read_rows(experiment_dir / "metrics.csv")
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("provider") or "unknown", row.get("model") or "unknown")].append(row)
    report: dict[str, Any] = {
        "experiment_id": manifest["experiment_id"],
        "result_class": manifest["result_class"],
        "formal_results_allowed": bool(manifest.get("formal_results_allowed", False)),
        "row_count": len(rows),
        "bootstrap_samples": bootstrap_samples,
        "seed": seed,
        "missing_output_policy": "exclude missing metric values before task/repetition pairing; retain failed rows as zeros where runner metrics define failure",
        "groups": {},
    }
    for group_index, ((provider, model), group_rows) in enumerate(sorted(grouped.items())):
        observed_conditions = {row["condition"] for row in group_rows}
        conditions = [
            condition
            for condition in manifest.get("conditions", [])
            if condition in observed_conditions
        ]
        conditions.extend(sorted(observed_conditions.difference(conditions)))
        descriptive: dict[str, Any] = {}
        for condition in conditions:
            condition_rows = [row for row in group_rows if row["condition"] == condition]
            descriptive[condition] = {}
            for metric in (*BINARY_METRICS, *CONTINUOUS_METRICS):
                values = [value for row in condition_rows if (value := _number(row, metric)) is not None]
                descriptive[condition][metric] = bootstrap_mean_ci(
                    values,
                    samples=bootstrap_samples,
                    seed=seed + group_index * 1000 + len(descriptive[condition]),
                )
            descriptive[condition]["refusal"] = _refusal_summary(group_rows, condition)
        tests: list[dict[str, Any]] = []
        for first, second in combinations(conditions, 2):
            for metric in (*BINARY_METRICS, *CONTINUOUS_METRICS):
                first_values, second_values = _pair_rows(group_rows, first, second, metric)
                if not first_values:
                    continue
                test = _mcnemar(first_values, second_values) if metric in BINARY_METRICS else _paired_rank_test(first_values, second_values)
                interval = _paired_bootstrap(
                    first_values,
                    second_values,
                    samples=bootstrap_samples,
                    seed=seed + len(tests),
                )
                tests.append(
                    {
                        "comparison": f"{first}_vs_{second}",
                        "first": first,
                        "second": second,
                        "metric": metric,
                        "n": len(first_values),
                        **test,
                        **interval,
                    }
                )
        _holm_adjust(tests)
        category_breakdown: dict[str, Any] = {}
        categories = sorted({row["category"] for row in group_rows})
        for category in categories:
            category_breakdown[category] = {}
            for condition in conditions:
                selected = [row for row in group_rows if row["category"] == category and row["condition"] == condition]
                category_breakdown[category][condition] = {
                    metric: mean(values) if (values := [value for row in selected if (value := _number(row, metric)) is not None]) else None
                    for metric in ("task_success", "non_target_preservation", "operation_minimality", "constraint_satisfaction")
                }
        report["groups"][f"{provider}:{model}"] = {
            "provider": provider,
            "model": model,
            "conditions": conditions,
            "descriptive": descriptive,
            "paired_tests": tests,
            "category_breakdown": category_breakdown,
        }
    (experiment_dir / "statistics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (experiment_dir / "statistics.md").write_text(_markdown(report), encoding="utf-8")
    return report

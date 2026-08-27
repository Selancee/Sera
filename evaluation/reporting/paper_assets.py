"""Generate tables and information-bearing figures from experiment evidence."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from evaluation.analysis.music_statistics import parse_pitch_name
from evaluation.error_analysis.taxonomy import build_error_taxonomy
from evaluation.statistics.paired_analysis import analyze_experiment


DISPLAY_NAMES = {
    "full_rewrite": "Full Rewrite",
    "patch_only": "ScorePatch Only",
    "sera_full": "Sera Full",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _values(rows: list[dict[str, str]], field: str) -> list[float]:
    result: list[float] = []
    for row in rows:
        raw = row.get(field, "")
        if raw is None or str(raw).strip() == "":
            continue
        try:
            result.append(float(raw))
        except ValueError:
            continue
    return result


def _fmt(value: float | None, digits: int = 3) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def _write_table(base: Path, rows: list[dict[str, Any]], caption: str) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with base.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    markdown = [f"<!-- {caption} -->", "", "| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    markdown.extend("| " + " | ".join(str(row[field]) for field in fields) + " |" for row in rows)
    base.with_suffix(".md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    escaped_caption = caption.replace("_", "\\_")
    latex = ["\\begin{table}[t]", "\\centering", f"\\caption{{{escaped_caption}}}", "\\small", "\\begin{tabular}{" + "l" * len(fields) + "}", "\\hline", " & ".join(field.replace("_", "\\_") for field in fields) + " \\\\", "\\hline"]
    for row in rows:
        latex.append(" & ".join(str(row[field]).replace("_", "\\_") for field in fields) + " \\\\")
    latex.extend(["\\hline", "\\end{tabular}", "\\end{table}", ""])
    base.with_suffix(".tex").write_text("\n".join(latex), encoding="utf-8")


def _save_figure(fig: plt.Figure, base: Path) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _watermark(fig: plt.Figure, result_class: str) -> None:
    if result_class != "formal_live":
        fig.text(
            0.5,
            0.5,
            "NON-FORMAL MOCK / PIPELINE CHECK ONLY",
            ha="center",
            va="center",
            rotation=28,
            fontsize=18,
            color="0.5",
            alpha=0.18,
            weight="bold",
        )


def _main_table(rows: list[dict[str, str]], conditions: list[str], result_class: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for condition in conditions:
        selected = [row for row in rows if row["condition"] == condition]
        successes = sum(_values(selected, "task_success"))
        cost = sum(_values(selected, "estimated_cost"))
        metric = lambda field: mean(values) if (values := _values(selected, field)) else None  # noqa: E731
        result.append(
            {
                "Method": DISPLAY_NAMES.get(condition, condition),
                "XML Validity": _fmt(metric("musicxml_validity")),
                "Patch Parse": _fmt(metric("patch_parse")),
                "Task Success": _fmt(metric("task_success")),
                "Preservation": _fmt(metric("non_target_preservation")),
                "Minimality": _fmt(metric("operation_minimality")),
                "Constraints": _fmt(metric("constraint_satisfaction")),
                "Median ms": _fmt(median(_values(selected, "latency_ms")) if _values(selected, "latency_ms") else None, 1),
                "Cost/success": _fmt(cost / successes if successes else None, 6),
                "Result class": result_class,
            }
        )
    return result


def _category_table(rows: list[dict[str, str]], conditions: list[str]) -> list[dict[str, Any]]:
    result = []
    for category in sorted({row["category"] for row in rows}):
        row: dict[str, Any] = {"Category": category}
        for condition in conditions:
            selected = [item for item in rows if item["category"] == category and item["condition"] == condition]
            values = _values(selected, "task_success")
            row[DISPLAY_NAMES.get(condition, condition)] = _fmt(mean(values) if values else None)
        result.append(row)
    return result


def _benchmark_distribution(benchmark_root: Path, figure_root: Path, result_class: str) -> None:
    split = json.loads((benchmark_root / "splits" / "core.json").read_text(encoding="utf-8"))
    labels = list(split["category_counts"])
    values = [split["category_counts"][label] for label in labels]
    fig, ax = plt.subplots(figsize=(8.2, 4.5))
    bars = ax.barh(labels, values, color="0.75", edgecolor="black", hatch="//")
    ax.bar_label(bars, padding=3)
    ax.set_xlabel("Number of tasks")
    ax.set_title("SeraEdit Core benchmark composition")
    ax.set_xlim(0, max(values) + 3)
    _watermark(fig, result_class)
    _save_figure(fig, figure_root / "benchmark_category_distribution")


def _main_metric_figure(rows: list[dict[str, str]], conditions: list[str], figure_root: Path, result_class: str) -> None:
    metrics = ["task_success", "non_target_preservation", "operation_minimality", "constraint_satisfaction"]
    labels = ["Task success", "Preservation", "Minimality", "Constraints"]
    width = 0.24
    fig, ax = plt.subplots(figsize=(8.2, 4.5))
    x = list(range(len(metrics)))
    hatches = ["//", "xx", ".."]
    colors = ["0.85", "0.6", "0.35"]
    for index, condition in enumerate(conditions):
        selected = [row for row in rows if row["condition"] == condition]
        means = [mean(values) if (values := _values(selected, metric)) else 0 for metric in metrics]
        ax.bar(
            [value + (index - (len(conditions) - 1) / 2) * width for value in x],
            means,
            width,
            label=DISPLAY_NAMES.get(condition, condition),
            color=colors[index % len(colors)],
            edgecolor="black",
            hatch=hatches[index % len(hatches)],
        )
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Rate")
    ax.set_title("Primary edit metrics", pad=10)
    ax.legend(frameon=False, ncol=len(conditions), loc="lower center", bbox_to_anchor=(0.5, 1.12))
    fig.subplots_adjust(top=0.78)
    _watermark(fig, result_class)
    _save_figure(fig, figure_root / "primary_metrics")


def _preservation_figure(rows: list[dict[str, str]], conditions: list[str], figure_root: Path, result_class: str) -> None:
    data = [_values([row for row in rows if row["condition"] == condition], "non_target_preservation") for condition in conditions]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    box = ax.boxplot(data, tick_labels=[DISPLAY_NAMES.get(item, item) for item in conditions], patch_artist=True)
    for index, patch in enumerate(box["boxes"]):
        patch.set(facecolor=["0.85", "0.6", "0.35"][index % 3], edgecolor="black", hatch=["//", "xx", ".."][index % 3])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Non-target preservation")
    ax.set_title("Task-level protected-scope preservation")
    _watermark(fig, result_class)
    _save_figure(fig, figure_root / "preservation_comparison")


def _error_figure(taxonomy: list[dict[str, Any]], figure_root: Path, result_class: str) -> None:
    nonzero = [row for row in taxonomy if int(row["occurrences"]) > 0]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    if nonzero:
        labels = [f"{row['error_code']} {row['name']}" for row in nonzero]
        values = [int(row["occurrences"]) for row in nonzero]
        bars = ax.barh(labels, values, color="0.65", edgecolor="black", hatch="//")
        ax.bar_label(bars, padding=3)
        ax.set_xlabel("Occurrences")
    else:
        ax.text(0.5, 0.5, "No error codes in this run", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
    ax.set_title("SeraEdit error taxonomy")
    _watermark(fig, result_class)
    _save_figure(fig, figure_root / "error_distribution")


def _case_figure(benchmark_root: Path, figure_root: Path, result_class: str) -> None:
    task = json.loads((benchmark_root / "tasks" / "batch1" / "pitch_001.json").read_text(encoding="utf-8"))
    before = json.loads((benchmark_root / "source_scores" / f"{task['score_id']}.score.json").read_text(encoding="utf-8"))
    after = json.loads((benchmark_root / task["expected_output_path"]).read_text(encoding="utf-8"))
    before_events = {event["event_id"]: (measure["number"], event) for measure in before["measures"] for event in measure["events"] if event.get("type") == "note" and event.get("staff") == "right_hand"}
    after_events = {event["event_id"]: (measure["number"], event) for measure in after["measures"] for event in measure["events"] if event.get("type") == "note" and event.get("staff") == "right_hand"}
    ids = [event_id for event_id in before_events if event_id in after_events]
    x = [(before_events[event_id][0] - 1) * 4 + float(before_events[event_id][1].get("offset", 0)) for event_id in ids]
    old_y = [parse_pitch_name(str(before_events[event_id][1].get("pitch"))) or 0 for event_id in ids]
    new_y = [parse_pitch_name(str(after_events[event_id][1].get("pitch"))) or 0 for event_id in ids]
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.scatter(x, old_y, marker="o", facecolors="white", edgecolors="black", label="Before", s=55)
    ax.scatter(x, new_y, marker="x", color="black", label="After", s=55)
    for x_value, old, new in zip(x, old_y, new_y, strict=True):
        if old != new:
            ax.plot([x_value, x_value], [old, new], color="0.5", linestyle="--", linewidth=0.8)
    ax.axvspan(-0.2, 3.8, facecolor="0.9", hatch="//", edgecolor="0.7", alpha=0.5, label="Target measure")
    ax.set_xlabel("Quarter-note position")
    ax.set_ylabel("MIDI pitch")
    ax.set_title("Event-level case: pitch_001 (+2 semitones in measure 1)")
    ax.legend(frameon=False, ncol=3)
    _watermark(fig, result_class)
    _save_figure(fig, figure_root / "score_edit_case_pitch_001")


def generate_paper_assets(root: Path, experiment_id: str, *, bootstrap_samples: int = 5000) -> dict[str, Any]:
    """Generate all deterministic tables/plots for one experiment."""

    experiment_dir = root / "experiments" / experiment_id
    manifest = json.loads((experiment_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = _read_csv(experiment_dir / "metrics.csv")
    result_class = str(manifest["result_class"])
    conditions = [condition for condition in manifest["conditions"] if any(row["condition"] == condition for row in rows)]
    table_root = root / "paper" / "tables"
    figure_root = root / "paper" / "figures"
    caption_prefix = "NON-FORMAL MOCK PLACEHOLDER. " if result_class != "formal_live" else ""
    _write_table(table_root / f"{experiment_id}_main_results", _main_table(rows, conditions, result_class), caption_prefix + "Main SeraEdit results generated from experiment metrics.")
    _write_table(table_root / f"{experiment_id}_category_results", _category_table(rows, conditions), caption_prefix + "Task success by benchmark category.")
    taxonomy = build_error_taxonomy(experiment_dir / "metrics.csv", table_root / "error_taxonomy.csv")
    analyze_experiment(experiment_dir, bootstrap_samples=bootstrap_samples)
    benchmark_root = root / "benchmark"
    _benchmark_distribution(benchmark_root, figure_root, result_class)
    _main_metric_figure(rows, conditions, figure_root, result_class)
    _preservation_figure(rows, conditions, figure_root, result_class)
    _error_figure(taxonomy, figure_root, result_class)
    _case_figure(benchmark_root, figure_root, result_class)
    captions = {
        "benchmark_category_distribution": "Core benchmark category distribution (120 tasks).",
        "primary_metrics": caption_prefix + "Primary metrics for the three experimental conditions.",
        "preservation_comparison": caption_prefix + "Task-level non-target preservation by condition.",
        "error_distribution": caption_prefix + "Observed failures mapped to the fixed error taxonomy.",
        "score_edit_case_pitch_001": "Event-level before/after view of a deterministic benchmark transposition; this is not an engraving-quality score rendering.",
    }
    (figure_root / "CAPTIONS.md").write_text("\n".join(f"- **{name}:** {caption}" for name, caption in captions.items()) + "\n", encoding="utf-8")
    metadata = {
        "experiment_id": experiment_id,
        "result_class": result_class,
        "formal_results_allowed": bool(manifest.get("formal_results_allowed", False)),
        "warning": None if result_class == "formal_live" else "Generated assets are non-formal placeholders and must not be used as model-performance evidence.",
        "tables": 2,
        "figures": 5,
    }
    (root / "paper" / "ASSET_MANIFEST.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata

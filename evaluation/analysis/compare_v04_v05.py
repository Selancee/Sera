"""Compare V0.4 and V0.5 musicality evaluation rows."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


METRIC_KEYS = [
    "musicxml_validity_rate",
    "midi_export_success_rate",
    "rhythmic_diversity_score",
    "quarter_note_dominance_score",
    "melodic_interval_variety_score",
    "stepwise_overuse_penalty",
    "cadence_presence_score",
    "overall_musicality_proxy_score",
    "average_generation_time",
]


def summarize_by_mode(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Average V0.5 comparison rows by generator mode."""

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get("generator_mode", "unknown"))].append(row)
    summary: dict[str, dict[str, float]] = {}
    for mode, items in buckets.items():
        summary[mode] = {
            key: sum(float(item.get(key, 0.0)) for item in items) / max(1, len(items))
            for key in METRIC_KEYS
        }
        summary[mode]["count"] = float(len(items))
    return summary


def latex_table(summary: dict[str, dict[str, float]]) -> str:
    """Return a compact ablation table."""

    lines = [
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "Mode & Valid & Rhythm div. & Cadence & Overall \\\\",
        "\\midrule",
    ]
    for mode, metrics in sorted(summary.items()):
        lines.append(
            f"{mode} & {metrics.get('musicxml_validity_rate', 0):.3f} & "
            f"{metrics.get('rhythmic_diversity_score', 0):.3f} & "
            f"{metrics.get('cadence_presence_score', 0):.3f} & "
            f"{metrics.get('overall_musicality_proxy_score', 0):.3f} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    return "\n".join(lines)

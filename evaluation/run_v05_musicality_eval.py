"""Run V0.4 vs V0.5 musicality comparison experiments."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.pipeline import SeraPipeline
from evaluation.analysis.compare_v04_v05 import latex_table, summarize_by_mode


MODES = [
    ("v04_model_based", "model_based"),
    ("v04_rule_based", "rule_based"),
    ("v05_model_fragment", "hybrid_v05_no_postprocess"),
    ("v05_hybrid", "hybrid_v05"),
    ("v05_hybrid_without_postprocess", "hybrid_v05_no_postprocess"),
]


def load_prompts(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        {"id": str(item.get("id", f"prompt_{index:03d}")), "prompt": str(item["prompt"]), "category": str(item.get("category", ""))}
        for index, item in enumerate(data, start=1)
    ]


def run_eval(prompts: list[dict[str, str]], project_root: Path, max_prompts: int = 0) -> list[dict[str, Any]]:
    pipeline = SeraPipeline(project_root)
    rows: list[dict[str, Any]] = []
    selected = prompts[:max_prompts] if max_prompts else prompts
    for item in selected:
        for label, backend in MODES:
            started = time.perf_counter()
            record = pipeline.generate(item["prompt"], generator_mode=backend)
            evaluation = record.get("evaluation", {})
            rows.append(
                {
                    "prompt_id": item["id"],
                    "category": item["category"],
                    "prompt": item["prompt"],
                    "run_id": record.get("run_id"),
                    "generator_mode": label,
                    "backend": backend,
                    "average_generation_time": evaluation.get("average_generation_time", round(time.perf_counter() - started, 4)),
                    **evaluation,
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_plots(plot_dir: Path, summary: dict[str, dict[str, float]]) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError:
        (plot_dir / "README.txt").write_text("matplotlib not installed; CSV/JSON/TeX outputs were written.\n", encoding="utf-8")
        return
    modes = list(summary)
    overall = [summary[mode].get("overall_musicality_proxy_score", 0.0) for mode in modes]
    plt.figure(figsize=(9, 4))
    plt.bar(modes, overall)
    plt.xticks(rotation=25, ha="right")
    plt.ylabel("overall musicality proxy")
    plt.tight_layout()
    plt.savefig(plot_dir / "overall_musicality_proxy.png", dpi=160)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default="evaluation/prompt_sets/v05_musicality_30.json")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--max-prompts", type=int, default=0)
    parser.add_argument("--out-csv", default="evaluation/results/v05_musicality_results.csv")
    parser.add_argument("--out-summary", default="evaluation/results/v05_musicality_summary.json")
    parser.add_argument("--out-tex", default="evaluation/results/v05_ablation_table.tex")
    parser.add_argument("--plot-dir", default="evaluation/results/v05_musicality_plots")
    args = parser.parse_args()

    rows = run_eval(load_prompts(Path(args.prompts)), Path(args.project_root), args.max_prompts)
    summary = summarize_by_mode(rows)
    write_csv(Path(args.out_csv), rows)
    Path(args.out_summary).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_summary).write_text(json.dumps({"rows": len(rows), "summary": summary}, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.out_tex).write_text(latex_table(summary), encoding="utf-8")
    write_plots(Path(args.plot_dir), summary)
    print(f"Wrote {args.out_csv}, {args.out_summary}, and {args.out_tex}")


if __name__ == "__main__":
    main()

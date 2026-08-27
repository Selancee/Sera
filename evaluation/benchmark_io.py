"""Shared, deterministic benchmark asset resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def resolve_task_path(benchmark_root: Path, task_id: str, preferred_split: str | None = None) -> Path:
    """Resolve one task across incremental batches without silently picking duplicates."""

    if preferred_split:
        preferred = benchmark_root / "tasks" / preferred_split / f"{task_id}.json"
        if preferred.exists():
            return preferred
    candidates = sorted((benchmark_root / "tasks").glob(f"*/{task_id}.json"))
    if not candidates:
        raise FileNotFoundError(f"benchmark task file missing: {task_id}")
    if len(candidates) > 1:
        relative = [str(path.relative_to(benchmark_root)).replace("\\", "/") for path in candidates]
        raise ValueError(f"benchmark task id is ambiguous: {task_id}: {relative}")
    return candidates[0]


def load_task(benchmark_root: Path, task_id: str, preferred_split: str | None = None) -> dict[str, Any]:
    """Load one benchmark task using the incremental-batch resolver."""

    return json.loads(resolve_task_path(benchmark_root, task_id, preferred_split).read_text(encoding="utf-8"))

"""Experiment logging for reproducible Sera runs."""

from __future__ import annotations

import json
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ExperimentLogger:
    """Append-only JSONL logger for prompts, plans, artifacts, and metrics."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.metadata_dir = self.project_root / "data" / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.metadata_dir / "experiment_logs.jsonl"
        self.experiments_dir = self.project_root / "experiments"
        self.experiments_dir.mkdir(parents=True, exist_ok=True)

    def new_run_id(self, prompt: str = "") -> str:
        """Create a timestamp plus prompt-hash run id."""

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:8] if prompt else "noprompt"
        return f"{stamp}_{digest}"

    def experiment_dir(self, run_id: str) -> Path:
        """Return the independent experiment folder for one run."""

        target = self.experiments_dir / run_id
        target.mkdir(parents=True, exist_ok=True)
        return target

    def append(self, record: dict[str, Any]) -> None:
        """Append one experiment record to disk."""

        enriched = {"created_at": datetime.now(UTC).isoformat(), **record}
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")

    @staticmethod
    def write_json(path: str | Path, payload: dict[str, Any] | list[Any]) -> Path:
        """Write a JSON artifact for one experiment run."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @staticmethod
    def write_text(path: str | Path, payload: str) -> Path:
        """Write a text artifact for one experiment run."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
        return target

    def list_records(self, limit: int = 50, dedupe: bool = True) -> list[dict[str, Any]]:
        """Return the most recent experiment records.

        Rating updates append a newer copy of the same run, so the default list
        view deduplicates by run id while preserving the append-only JSONL log.
        """

        if not self.log_path.exists():
            return []
        records = []
        with self.log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        if not dedupe:
            return records[-limit:][::-1]
        seen: set[str] = set()
        latest: list[dict[str, Any]] = []
        for record in reversed(records):
            run_id = str(record.get("run_id", ""))
            if run_id and run_id in seen:
                continue
            if run_id:
                seen.add(run_id)
            latest.append(record)
            if len(latest) >= limit:
                break
        return latest

    def get_record(self, run_id: str) -> dict[str, Any] | None:
        """Return the newest record for a run id."""

        for record in self.list_records(limit=1000):
            if record.get("run_id") == run_id:
                return record
        return None

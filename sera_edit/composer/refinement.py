"""In-memory background jobs for non-blocking live-LLM Composer refinement."""

from __future__ import annotations

import copy
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class _RefinementJob:
    job_id: str
    created_at: float
    status: str = "running"
    completed_at: float | None = None
    result: dict[str, Any] | None = None
    error: str = ""
    thread: threading.Thread | None = field(default=None, repr=False)


class ComposerRefinementStore:
    """Run bounded LLM planning without holding the interactive HTTP response."""

    def __init__(self, *, max_jobs: int = 16, ttl_seconds: float = 900.0) -> None:
        self.max_jobs = max(2, int(max_jobs))
        self.ttl_seconds = max(60.0, float(ttl_seconds))
        self._jobs: dict[str, _RefinementJob] = {}
        self._lock = threading.RLock()

    def start(self, worker: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        """Start one daemon worker and return a credential-free public snapshot."""

        job_id = f"composer_refine_{uuid.uuid4().hex[:20]}"
        job = _RefinementJob(job_id=job_id, created_at=time.time())
        thread = threading.Thread(
            target=self._run,
            args=(job_id, worker),
            name=f"sera-{job_id}",
            daemon=True,
        )
        job.thread = thread
        with self._lock:
            self._prune_locked()
            if len(self._jobs) >= self.max_jobs:
                raise RuntimeError("后台 LLM 优化任务已满，请稍后重试；本地 Composer 仍可使用。")
            self._jobs[job_id] = job
        thread.start()
        return self.get(job_id)

    def get(self, job_id: str) -> dict[str, Any]:
        """Return a defensive snapshot; completed score data stays process-local."""

        with self._lock:
            self._prune_locked()
            job = self._jobs.get(str(job_id))
            if job is None:
                raise KeyError(job_id)
            payload = {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at,
                "completed_at": job.completed_at,
                "error": job.error,
            }
            if job.status == "ready" and job.result is not None:
                payload["result"] = copy.deepcopy(job.result)
            return payload

    def clear(self) -> None:
        """Drop completed test/runtime metadata without attempting unsafe thread cancellation."""

        with self._lock:
            self._jobs = {key: value for key, value in self._jobs.items() if value.status == "running"}

    def _run(self, job_id: str, worker: Callable[[], dict[str, Any]]) -> None:
        try:
            result = worker()
            if (result.get("planner") or {}).get("planner") != "live_llm":
                reason = str((result.get("planner") or {}).get("fallback_reason") or "LLM 未生成合法高层计划。")
                raise RuntimeError(reason)
        except Exception as exc:  # noqa: BLE001 - provider failures must degrade to the local draft.
            with self._lock:
                job = self._jobs.get(job_id)
                if job is not None:
                    job.status = "failed"
                    job.error = _safe_error(exc)
                    job.completed_at = time.time()
            return
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.status = "ready"
                job.result = copy.deepcopy(result)
                job.completed_at = time.time()

    def _prune_locked(self) -> None:
        now = time.time()
        expired = [
            key
            for key, value in self._jobs.items()
            if value.status != "running" and now - (value.completed_at or value.created_at) > self.ttl_seconds
        ]
        for key in expired:
            self._jobs.pop(key, None)
        completed = sorted(
            (value for value in self._jobs.values() if value.status != "running"),
            key=lambda value: value.completed_at or value.created_at,
        )
        while len(self._jobs) >= self.max_jobs and completed:
            self._jobs.pop(completed.pop(0).job_id, None)


def _safe_error(exc: Exception) -> str:
    message = str(exc).replace("\r", " ").replace("\n", " ").strip()
    return (message or exc.__class__.__name__)[:500]


_DEFAULT_STORE = ComposerRefinementStore()


def default_composer_refinement_store() -> ComposerRefinementStore:
    return _DEFAULT_STORE

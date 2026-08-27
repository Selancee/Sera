"""Thread-safe handoff from notation-host requests to the Sera desktop shell."""

from __future__ import annotations

import os
import threading
from datetime import UTC, datetime
from typing import Any


class DesktopSessionBroker:
    """Keep the latest host-created bridge session for Electron polling."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sequence = 0
        self._session_id = ""
        self._published_at = ""

    def desktop_available(self) -> bool:
        """Return whether this backend was launched by the desktop shell."""

        return os.getenv("SERA_DESKTOP_MODE", "").strip() == "1"

    def publish(self, session_id: str) -> dict[str, Any]:
        """Publish a safe bridge session id and return its delivery snapshot."""

        value = str(session_id or "").strip()
        if not value.startswith("bridge_"):
            raise ValueError("Desktop bridge session id must start with 'bridge_'.")
        with self._lock:
            self._sequence += 1
            self._session_id = value
            self._published_at = datetime.now(UTC).isoformat()
            return self._snapshot_locked(after_sequence=self._sequence - 1)

    def snapshot(self, after_sequence: int = 0, after_backend_pid: int = 0) -> dict[str, Any]:
        """Return sessions newer than the caller cursor or from a new backend."""

        with self._lock:
            return self._snapshot_locked(
                after_sequence=max(0, int(after_sequence)),
                after_backend_pid=max(0, int(after_backend_pid)),
            )

    def reset(self) -> None:
        """Clear in-memory delivery state for isolated tests."""

        with self._lock:
            self._sequence = 0
            self._session_id = ""
            self._published_at = ""

    def _snapshot_locked(self, after_sequence: int, after_backend_pid: int = 0) -> dict[str, Any]:
        backend_pid = os.getpid()
        backend_changed = after_backend_pid > 0 and after_backend_pid != backend_pid
        pending = bool(self._session_id) and (backend_changed or self._sequence > after_sequence)
        return {
            "desktop_available": self.desktop_available(),
            "backend_pid": backend_pid,
            "sequence": self._sequence,
            "pending": pending,
            "session_id": self._session_id if pending else "",
            "published_at": self._published_at if pending else "",
            "delivery_mode": "electron_ipc" if self.desktop_available() else "desktop_not_running",
        }


desktop_session_broker = DesktopSessionBroker()

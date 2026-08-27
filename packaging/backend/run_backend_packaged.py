"""Runtime entrypoint for a packaged Sera FastAPI backend."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import app


def find_available_port(start: int = 8000, max_attempts: int = 25, host: str = "127.0.0.1") -> int:
    """Return the first free localhost TCP port at or above ``start``."""

    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No available port found from {start} to {start + max_attempts - 1}.")


def resolve_backend_port(start: int, host: str = "127.0.0.1") -> int:
    """Use a fixed port for notation plug-ins, or a fallback range outside desktop mode."""

    attempts = 1 if os.getenv("SERA_DESKTOP_STRICT_PORT", "").strip() == "1" else 25
    return find_available_port(start, max_attempts=attempts, host=host)


def runtime_dir() -> Path:
    target = Path(os.getenv("SERA_RUNTIME_DIR", Path.home() / "AppData" / "Local" / "Sera"))
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_runtime_port_file(port: int, target_dir: Path | None = None) -> Path:
    target = (target_dir or runtime_dir()) / "backend_port.json"
    target.write_text(
        json.dumps(
            {
                "host": "127.0.0.1",
                "port": int(port),
                "base_url": f"http://127.0.0.1:{int(port)}",
                "pid": os.getpid(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return target


def main() -> None:
    preferred = int(os.getenv("SERA_BACKEND_PORT", "8000"))
    port = resolve_backend_port(preferred)
    write_runtime_port_file(port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level=os.getenv("SERA_LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()

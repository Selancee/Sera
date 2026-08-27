"""Legacy packaged local-server launcher for Sera.

This executable serves the built frontend from the same FastAPI process as the
backend API and writes the runtime port file.  It does not open an external
browser unless the explicit compatibility flag is enabled; Electron is the
supported desktop user interface.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import app


API_PREFIXES = {
    "docs",
    "openapi.json",
    "redoc",
    "health",
    "generate",
    "revise",
    "rate",
    "evaluate",
    "experiments",
    "export",
    "integrations",
    "model",
    "score",
}


def find_available_port(start: int = 8000, max_attempts: int = 25, host: str = "127.0.0.1") -> int:
    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No available port found from {start} to {start + max_attempts - 1}.")


def runtime_dir() -> Path:
    default_base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    target = Path(os.getenv("SERA_RUNTIME_DIR", Path(default_base) / "Sera"))
    target.mkdir(parents=True, exist_ok=True)
    return target


def log_runtime(message: str) -> None:
    try:
        target = runtime_dir() / "desktop_launcher.log"
        with target.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")
    except Exception:
        pass


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


def frontend_dist_dir() -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    bundled = bundle_root / "frontend_dist"
    if bundled.exists():
        return bundled
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def configure_frontend_routes(application: FastAPI, frontend_dir: Path | None = None) -> None:
    frontend = frontend_dir or frontend_dist_dir()
    index = frontend / "index.html"
    assets = frontend / "assets"
    if assets.exists():
        application.mount("/assets", StaticFiles(directory=str(assets)), name="desktop_assets")

    @application.get("/", include_in_schema=False)
    async def desktop_index() -> FileResponse:
        return FileResponse(index)

    @application.get("/{path:path}", include_in_schema=False)
    async def desktop_spa_fallback(path: str) -> FileResponse:
        first_segment = path.split("/", 1)[0]
        if first_segment in API_PREFIXES:
            return FileResponse(index, status_code=404)
        return FileResponse(index)


def open_browser_later(url: str) -> None:
    if os.getenv("SERA_ALLOW_EXTERNAL_BROWSER", "").strip() != "1":
        return
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


def main() -> None:
    try:
        preferred = int(os.getenv("SERA_DESKTOP_PORT", os.getenv("SERA_BACKEND_PORT", "8000")))
        port = find_available_port(preferred)
        frontend = frontend_dist_dir()
        log_runtime(f"starting desktop launcher on port {port}")
        log_runtime(f"frontend_dist={frontend}")
        write_runtime_port_file(port)
        configure_frontend_routes(app, frontend)
        url = f"http://127.0.0.1:{port}/"
        open_browser_later(url)
        log_runtime(f"starting uvicorn at {url}")
        uvicorn.run(app, host="127.0.0.1", port=port, log_level=os.getenv("SERA_LOG_LEVEL", "info"), log_config=None)
    except Exception:
        log_runtime(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()

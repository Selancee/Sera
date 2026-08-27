"""MuseScore 4 bridge fallback using saved score files and the MuseScore CLI.

MuseScore Studio 4.5.2 exposes QML ``writeScore``/``readScore`` symbols but
logs both operations as ``Not implemented!!``.  This service keeps the bridge
local and non-destructive while avoiding those unavailable plugin methods.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from backend.integrations.notation_hosts import resolve_musescore_executable


class MuseScoreFileBridgeError(RuntimeError):
    """Raised when a saved MuseScore file cannot enter or leave the bridge."""


class MuseScoreFileBridgeService:
    """Convert saved MuseScore files to MusicXML and open reviewed revisions."""

    _ALLOWED_SOURCE_SUFFIXES = {".mscz", ".mscx", ".mxl", ".musicxml", ".xml"}
    _ALLOWED_REVIEW_SUFFIXES = {".musicxml", ".xml"}

    def __init__(
        self,
        project_root: str | Path,
        *,
        executable_resolver: Callable[[], str] = resolve_musescore_executable,
        runner: Callable[..., Any] = subprocess.run,
        opener: Callable[..., Any] = subprocess.Popen,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.project_root = Path(project_root)
        self._executable_resolver = executable_resolver
        self._runner = runner
        self._opener = opener
        self.timeout_seconds = float(timeout_seconds)

    def import_saved_score(self, source_path: str) -> dict[str, Any]:
        """Read MusicXML directly or convert a saved MuseScore file via CLI."""

        source = _resolve_local_path(source_path)
        if source.suffix.lower() not in self._ALLOWED_SOURCE_SUFFIXES:
            allowed = ", ".join(sorted(self._ALLOWED_SOURCE_SUFFIXES))
            raise MuseScoreFileBridgeError(f"Unsupported MuseScore bridge file '{source.suffix}'. Allowed: {allowed}.")
        if source.stat().st_size <= 0:
            raise MuseScoreFileBridgeError("The selected score file is empty.")

        started = time.perf_counter()
        if source.suffix.lower() in {".musicxml", ".xml"}:
            try:
                musicxml = source.read_text(encoding="utf-8-sig")
            except UnicodeError as exc:
                raise MuseScoreFileBridgeError(f"The selected MusicXML file is not valid UTF-8: {exc}") from exc
            mode = "direct_musicxml"
            executable = ""
        else:
            executable = self._require_executable()
            with tempfile.TemporaryDirectory(prefix="sera_musescore_bridge_") as temporary:
                output_path = Path(temporary) / "source.musicxml"
                command = [executable, str(source), "-o", str(output_path)]
                try:
                    completed = self._runner(
                        command,
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout_seconds,
                        check=False,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise MuseScoreFileBridgeError(
                        f"MuseScore CLI did not finish within {self.timeout_seconds:g} seconds."
                    ) from exc
                except OSError as exc:
                    raise MuseScoreFileBridgeError(f"MuseScore CLI could not start: {exc}") from exc
                if int(getattr(completed, "returncode", 1)) != 0 or not output_path.is_file():
                    details = str(getattr(completed, "stderr", "") or getattr(completed, "stdout", "")).strip()
                    details = details[:500] or "no MusicXML output was created"
                    raise MuseScoreFileBridgeError(f"MuseScore CLI conversion failed: {details}")
                musicxml = output_path.read_text(encoding="utf-8-sig")
            mode = "musescore_cli"

        if "<score-partwise" not in musicxml and "<score-timewise" not in musicxml:
            raise MuseScoreFileBridgeError("MuseScore conversion did not return a recognizable MusicXML score.")
        return {
            "musicxml": musicxml,
            "source_path": str(source),
            "source_name": source.name,
            "source_suffix": source.suffix.lower(),
            "conversion_mode": mode,
            "musescore_executable": executable,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    def open_reviewed_score(self, score_path: str) -> dict[str, Any]:
        """Ask MuseScore to open a reviewed MusicXML artifact in a new tab."""

        score = _resolve_local_path(score_path)
        if score.suffix.lower() not in self._ALLOWED_REVIEW_SUFFIXES:
            raise MuseScoreFileBridgeError("Only reviewed MusicXML files may be opened in MuseScore.")
        executable = self._require_executable()
        try:
            process = self._opener([executable, str(score)], cwd=self.project_root, close_fds=True)
        except OSError as exc:
            raise MuseScoreFileBridgeError(f"MuseScore could not open the reviewed revision: {exc}") from exc
        return {
            "opened": True,
            "process_id": int(getattr(process, "pid", 0) or 0),
            "musescore_executable": executable,
            "score_path": str(score),
            "delivery_mode": "musescore_cli_open_new_tab",
        }

    def _require_executable(self) -> str:
        executable = str(self._executable_resolver() or "").strip()
        if not executable or not Path(executable).is_file():
            raise MuseScoreFileBridgeError(
                "MuseScore4.exe was not found. Set MUSESCORE_PATH or install MuseScore Studio 4."
            )
        return str(Path(executable).resolve())


def _resolve_local_path(value: str) -> Path:
    """Resolve a Windows path or file URL supplied by MuseScore's FileDialog."""

    raw = str(value or "").strip()
    if not raw:
        raise MuseScoreFileBridgeError("Choose a saved MuseScore or MusicXML file before sending the score.")
    parsed = urlparse(raw)
    if parsed.scheme.lower() == "file":
        raw = unquote(parsed.path)
        if parsed.netloc:
            raw = f"//{parsed.netloc}{raw}"
        elif len(raw) >= 3 and raw[0] == "/" and raw[2] == ":":
            raw = raw[1:]
    try:
        path = Path(raw).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise MuseScoreFileBridgeError(f"The selected score file does not exist or is inaccessible: {raw}") from exc
    if not path.is_file():
        raise MuseScoreFileBridgeError(f"The selected score path is not a file: {path}")
    return path

"""Backend preview rendering from real MusicXML sources."""

from __future__ import annotations

import shutil
import subprocess
import uuid
import os
from pathlib import Path
from typing import Any


class ScorePreviewRenderService:
    """Render MusicXML previews with external real notation tools when present."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "data" / "preview_renders"

    def renderer_status(self) -> dict[str, Any]:
        """Return real notation renderer availability and install hints."""

        musescore = _configured_executable("MUSESCORE_PATH", ["musescore", "MuseScore4", "MuseScore4.exe"])
        verovio = _configured_executable("VEROVIO_PATH", ["verovio"])
        warnings: list[str] = []
        if not musescore:
            warnings.append("MuseScore CLI not found. Backend professional preview rendering unavailable.")
        if not verovio:
            warnings.append("Verovio CLI not found. Backend SVG fallback rendering unavailable.")
        return {
            "musescore_available": bool(musescore),
            "musescore_path": musescore,
            "verovio_available": bool(verovio),
            "verovio_path": verovio,
            "backend_svg_supported": bool(musescore or verovio),
            "backend_png_supported": bool(musescore),
            "osmd_required_on_frontend": not bool(musescore or verovio),
            "warnings": warnings,
            "install_hints": {
                "windows_musescore": "Install MuseScore 4 and configure MUSESCORE_PATH or add MuseScore4.exe to PATH.",
                "verovio": "Install verovio and configure VEROVIO_PATH or add it to PATH.",
            },
        }

    def render_musicxml(self, musicxml: str, output_format: str = "svg", render_id: str | None = None) -> dict[str, Any]:
        """Render MusicXML to SVG/PNG/PDF, or return a structured unavailable result."""

        output_format = output_format.lower().strip(".")
        if output_format not in {"svg", "png", "pdf"}:
            return self._failure("unavailable", [f"Unsupported preview format: {output_format}"], musicxml)
        if not musicxml.strip():
            return self._failure("unavailable", ["No MusicXML text was provided."], musicxml)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        render_id = _safe_render_id(render_id or uuid.uuid4().hex[:12])
        musicxml_path = self.output_dir / f"{render_id}.musicxml"
        output_path = self.output_dir / f"{render_id}.{output_format}"
        musicxml_path.write_text(musicxml, encoding="utf-8")

        musescore = _configured_executable("MUSESCORE_PATH", ["musescore", "MuseScore4", "MuseScore4.exe"])
        if musescore:
            result = self._run_renderer([musescore, "-o", str(output_path), str(musicxml_path)], "musescore_cli", output_path, output_format, musicxml)
            if result["success"]:
                return result

        verovio = _configured_executable("VEROVIO_PATH", ["verovio"])
        if verovio and output_format == "svg":
            result = self._run_renderer([verovio, str(musicxml_path), "-o", str(output_path)], "verovio", output_path, output_format, musicxml)
            if result["success"]:
                return result

        errors = ["No real backend notation renderer is available."]
        if musescore:
            errors.append("MuseScore CLI was found but did not produce a readable preview.")
        if verovio and output_format != "svg":
            errors.append("Verovio is available only for SVG preview in this fallback path.")
        return self._failure("unavailable", errors, musicxml)

    def _run_renderer(self, command: list[str], renderer: str, output_path: Path, output_format: str, musicxml: str) -> dict[str, Any]:
        try:
            completed = subprocess.run(command, cwd=self.project_root, capture_output=True, text=True, timeout=20, check=False)
        except Exception as exc:  # noqa: BLE001 - report and fall through.
            return self._failure(renderer, [f"{renderer} failed to start: {exc}"], musicxml)
        if completed.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
            details = (completed.stderr or completed.stdout or "renderer returned no output").strip()
            return self._failure(renderer, [f"{renderer} failed: {details[:500]}"], musicxml)
        return self._success(renderer, output_path, output_format)

    @staticmethod
    def _success(renderer: str, output_path: Path, output_format: str) -> dict[str, Any]:
        urls = {"svg_url": "", "png_url": "", "pdf_url": ""}
        urls[f"{output_format}_url"] = f"/score/preview_render_artifact/{output_path.name}"
        return {
            "success": True,
            "renderer": renderer,
            **urls,
            "musicxml_text_available": True,
            "warnings": [],
            "errors": [],
        }

    @staticmethod
    def _failure(renderer: str, errors: list[str], musicxml: str) -> dict[str, Any]:
        return {
            "success": False,
            "renderer": renderer,
            "svg_url": "",
            "png_url": "",
            "pdf_url": "",
            "musicxml_text_available": bool(musicxml.strip()),
            "warnings": ["Preview falls back to real MusicXML text; no fake notation was generated."],
            "errors": errors,
        }


def _safe_render_id(value: str) -> str:
    cleaned = "".join(char for char in value if char.isalnum() or char in {"_", "-", "."}).strip(".")
    return cleaned[:80] or uuid.uuid4().hex[:12]


def _configured_executable(env_name: str, candidates: list[str]) -> str:
    configured = os.getenv(env_name, "").strip()
    if configured:
        path = Path(configured)
        if path.exists():
            return str(path)
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return ""

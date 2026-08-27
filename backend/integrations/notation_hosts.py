"""Host adapter contracts for MuseScore, Sibelius, and generic MusicXML exchange.

The first editing-layer milestones deliberately use versioned MusicXML files.
MuseScore has a thin QML artifact for localhost handoff, but it still opens a
reviewed revision in a new tab rather than mutating the source score in place.
Sibelius ManuScript can implement the same adapter contract later without
changing the ScoreDocument/ScorePatch core.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class NotationHostCapabilities:
    """Describe a notation host without overstating unverified automation."""

    host_id: str
    display_name: str
    exchange_mode: str
    import_formats: tuple[str, ...]
    export_formats: tuple[str, ...]
    executable_available: bool
    executable_path: str
    direct_roundtrip_available: bool
    bridge_status: str
    handoff_steps: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly capability payload."""

        payload = asdict(self)
        for key in ("import_formats", "export_formats", "handoff_steps", "limitations"):
            payload[key] = list(payload[key])
        return payload


class NotationHostAdapter(Protocol):
    """Stable extension point for file, plugin, or IPC notation bridges."""

    host_id: str

    def capabilities(self) -> NotationHostCapabilities:
        """Report currently verified host capabilities."""

    def revision_filename(self, session_id: str, revision: int) -> str:
        """Return a non-destructive exchange filename."""


class _MusicXMLAdapter:
    host_id = "musicxml"

    def capabilities(self) -> NotationHostCapabilities:
        return NotationHostCapabilities(
            host_id=self.host_id,
            display_name="Generic MusicXML",
            exchange_mode="versioned_file_exchange",
            import_formats=(".musicxml", ".xml"),
            export_formats=(".musicxml",),
            executable_available=False,
            executable_path="",
            direct_roundtrip_available=False,
            bridge_status="available",
            handoff_steps=(
                "Export or save MusicXML from the notation application.",
                "Import the MusicXML file into Sera and preview the agent patch.",
                "Export a new revision and open or import it in the notation application.",
            ),
            limitations=("File exchange is manual; no notation application is controlled directly.",),
        )

    def revision_filename(self, session_id: str, revision: int) -> str:
        return f"{session_id}_r{revision:04d}.musicxml"


class _MuseScoreAdapter(_MusicXMLAdapter):
    host_id = "musescore"

    def capabilities(self) -> NotationHostCapabilities:
        executable = resolve_musescore_executable()
        return NotationHostCapabilities(
            host_id=self.host_id,
            display_name="MuseScore Studio",
            exchange_mode="qml_saved_file_cli_bridge_versioned_musicxml",
            import_formats=(".musicxml", ".xml", ".mxl"),
            export_formats=(".musicxml",),
            executable_available=bool(executable),
            executable_path=executable,
            direct_roundtrip_available=False,
            bridge_status="musescore_4_5_cli_fallback_ready",
            handoff_steps=(
                "Save the score, run Sera Score Bridge, and choose that saved score file once.",
                "Send the saved file plus the current selection context to Sera Agent Console.",
                "Review and accept the patch, then ask the bridge to open the latest revision in a new MuseScore tab.",
            ),
            limitations=(
                "MuseScore 4.5.2 does not implement QML writeScore/readScore, so the bridge uses a saved-file picker and MuseScore CLI.",
                "Save current edits before sending; unsaved in-memory changes cannot be exported through the 4.5.2 plugin API.",
                "Reviewed output opens in a new tab; in-place apply and single-step host undo are not implemented.",
                "Sera never overwrites the original MSCZ or MusicXML file.",
            ),
        )


class _SibeliusAdapter(_MusicXMLAdapter):
    host_id = "sibelius"

    def capabilities(self) -> NotationHostCapabilities:
        executable = _configured_executable(
            "SIBELIUS_PATH",
            ("Sibelius.exe",),
            (
                Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Avid" / "Sibelius" / "Sibelius.exe",
                Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Avid" / "Sibelius Ultimate" / "Sibelius.exe",
            ),
        )
        return NotationHostCapabilities(
            host_id=self.host_id,
            display_name="Avid Sibelius Ultimate",
            exchange_mode="versioned_musicxml_file_exchange",
            import_formats=(".musicxml", ".xml", ".mxl"),
            export_formats=(".musicxml",),
            executable_available=bool(executable),
            executable_path=executable,
            direct_roundtrip_available=False,
            bridge_status="file_exchange_ready",
            handoff_steps=(
                "In Sibelius, export the current score as MusicXML.",
                "Import that MusicXML into Sera, request an edit, and accept the patch.",
                "Import the versioned MusicXML revision into Sibelius and save a new SIB file.",
            ),
            limitations=(
                "The ManuScript plug-in bridge is planned but not implemented in this milestone.",
                "MusicXML may not preserve every host-specific engraving property.",
            ),
        )


_ADAPTERS: dict[str, NotationHostAdapter] = {
    "musicxml": _MusicXMLAdapter(),
    "musescore": _MuseScoreAdapter(),
    "sibelius": _SibeliusAdapter(),
}


def adapter_for(host_id: str) -> NotationHostAdapter:
    """Resolve a notation host adapter or raise a readable error."""

    normalized = str(host_id or "musicxml").strip().lower()
    try:
        return _ADAPTERS[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(_ADAPTERS))
        raise ValueError(f"Unsupported notation host '{host_id}'. Supported hosts: {supported}.") from exc


def list_notation_host_capabilities() -> list[dict[str, object]]:
    """Return capabilities for every registered host adapter."""

    return [adapter.capabilities().to_dict() for adapter in _ADAPTERS.values()]


def resolve_musescore_executable() -> str:
    """Locate MuseScore across PATH, standard installs, and Windows drive-root installs."""

    program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
    drive_candidates = tuple(
        Path(f"{letter}:/MuseScore 4/bin/MuseScore4.exe") for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ"
    )
    return _configured_executable(
        "MUSESCORE_PATH",
        ("MuseScore4.exe", "MuseScore4", "musescore", "mscore"),
        (
            program_files / "MuseScore 4" / "bin" / "MuseScore4.exe",
            program_files_x86 / "MuseScore 4" / "bin" / "MuseScore4.exe",
            *drive_candidates,
        ),
    )


def _configured_executable(
    env_name: str,
    command_candidates: tuple[str, ...],
    path_candidates: tuple[Path, ...],
) -> str:
    configured = os.getenv(env_name, "").strip()
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())
    for command in command_candidates:
        found = shutil.which(command)
        if found:
            return found
    for path in path_candidates:
        if path.is_file():
            return str(path.resolve())
    return ""

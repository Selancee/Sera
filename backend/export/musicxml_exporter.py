"""MusicXML and ABC text exporters."""

from __future__ import annotations

from pathlib import Path


class MusicXMLExporter:
    """Persist symbolic text artifacts."""

    def write_musicxml(self, musicxml: str, path: str | Path) -> Path:
        """Write MusicXML text to disk."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(musicxml, encoding="utf-8")
        return target

    def write_abc(self, abc: str, path: str | Path) -> Path:
        """Write ABC notation text to disk."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(abc, encoding="utf-8")
        return target

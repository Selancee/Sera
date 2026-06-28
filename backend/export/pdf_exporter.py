"""PDF export helper.

The preferred future path is MuseScore CLI rendering from MusicXML. The MVP
writes a small valid PDF summary so the export route is functional even when
MuseScore is not installed.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class PDFExporter:
    """Export MusicXML to PDF with MuseScore when available, otherwise stub."""

    def write_pdf(self, musicxml_path: str | Path, pdf_path: str | Path, title: str) -> Path:
        """Write a PDF artifact for a generated score."""

        musicxml_path = Path(musicxml_path)
        pdf_path = Path(pdf_path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        musescore = self._find_musescore()
        if musescore:
            try:
                subprocess.run(
                    [musescore, str(musicxml_path), "-o", str(pdf_path)],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
                return pdf_path
            except (subprocess.SubprocessError, OSError):
                pass

        self._write_minimal_pdf(pdf_path, title, musicxml_path.name)
        return pdf_path

    @staticmethod
    def _find_musescore() -> str | None:
        for command in ("musescore", "mscore", "MuseScore4", "MuseScore3"):
            resolved = shutil.which(command)
            if resolved:
                return resolved
        return None

    @staticmethod
    def _write_minimal_pdf(path: Path, title: str, source_name: str) -> None:
        text = f"Sera score export\\n{title}\\nSource: {source_name}\\nInstall MuseScore CLI for engraved notation PDF."
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\n", "\\n")
        stream = f"BT /F1 14 Tf 72 740 Td ({escaped}) Tj ET".encode("ascii")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        ]
        chunks = [b"%PDF-1.4\n"]
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(sum(len(chunk) for chunk in chunks))
            chunks.append(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
        xref_offset = sum(len(chunk) for chunk in chunks)
        xref = [b"xref\n", f"0 {len(objects) + 1}\n".encode("ascii"), b"0000000000 65535 f \n"]
        for offset in offsets[1:]:
            xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
        trailer = (
            b"trailer\n"
            + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
            + b"startxref\n"
            + str(xref_offset).encode("ascii")
            + b"\n%%EOF\n"
        )
        path.write_bytes(b"".join(chunks + xref + [trailer]))

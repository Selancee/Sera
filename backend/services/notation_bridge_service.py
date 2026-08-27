"""Versioned MusicXML bridge sessions for external notation applications."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.integrations.notation_hosts import adapter_for, list_notation_host_capabilities
from backend.services.musicxml_source_patch_service import patch_musicxml_preserving_source
from backend.services.score_document_service import musicxml_to_score_document
from backend.validation.musicxml_validator import MusicXMLValidator


class NotationBridgeRevisionConflict(ValueError):
    """Raised when a client tries to export from a stale bridge revision."""


class NotationBridgeService:
    """Manage non-destructive imports and exports between Sera and score hosts."""

    def __init__(self, storage_root: str | Path) -> None:
        self.storage_root = Path(storage_root)
        self.validator = MusicXMLValidator()

    def list_hosts(self) -> list[dict[str, object]]:
        """Return verified host and exchange capabilities."""

        return list_notation_host_capabilities()

    def create_session(
        self,
        musicxml: str,
        host_id: str = "musicxml",
        source_name: str = "imported.musicxml",
        prompt: str = "",
        host_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Import MusicXML and create a revision-zero bridge session."""

        if not str(musicxml or "").strip():
            raise ValueError("MusicXML text is required to create a notation bridge session.")
        adapter = adapter_for(host_id)
        validation = self.validator.validate_text(musicxml).to_report()
        if not validation.get("valid_musicxml"):
            raise ValueError(f"MusicXML import validation failed: {validation.get('errors', [])}")
        score_document = musicxml_to_score_document(musicxml, prompt=prompt, source=f"{adapter.host_id}_bridge")
        session_id = f"bridge_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        session_dir = self.storage_root / session_id
        session_dir.mkdir(parents=True, exist_ok=False)
        source_path = session_dir / "source.musicxml"
        source_path.write_text(musicxml, encoding="utf-8")
        score_document_path = session_dir / "score_document.json"
        self._write_json(score_document_path, score_document)
        now = datetime.now(UTC).isoformat()
        digest = _sha256_text(musicxml)
        manifest: dict[str, Any] = {
            "schema_version": "1.1",
            "session_id": session_id,
            "host_id": adapter.host_id,
            "host_capabilities": adapter.capabilities().to_dict(),
            "host_context": _safe_host_context(host_context),
            "source_name": Path(source_name or "imported.musicxml").name,
            "source_artifact": str(source_path.resolve()),
            "score_document_artifact": str(score_document_path.resolve()),
            "source_sha256": digest,
            "current_sha256": digest,
            "revision": 0,
            "created_at": now,
            "updated_at": now,
            "artifacts": [
                {
                    "revision": 0,
                    "kind": "source",
                    "path": str(source_path.resolve()),
                    "sha256": digest,
                }
            ],
        }
        self._write_manifest(session_dir, manifest)
        return {
            "session": manifest,
            "score_document": score_document,
            "operation_history": {"done": [], "undone": []},
            "validation_report": validation,
        }

    def get_session(self, session_id: str) -> dict[str, Any]:
        """Load a bridge manifest by safe session id."""

        session_dir = self._session_dir(session_id)
        manifest_path = session_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Notation bridge session '{session_id}' was not found.")
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def get_workspace(self, session_id: str) -> dict[str, Any]:
        """Restore the canonical score and host selection for a browser deep link."""

        manifest = self.get_session(session_id)
        session_dir = self._session_dir(session_id)
        score_document_path = session_dir / "score_document.json"
        if score_document_path.is_file():
            score_document = json.loads(score_document_path.read_text(encoding="utf-8"))
        else:
            # Backward compatibility for bridge sessions created before schema 1.1.
            source_path = session_dir / "source.musicxml"
            if not source_path.is_file():
                raise FileNotFoundError(f"Notation bridge session '{session_id}' has no canonical score artifact.")
            score_document = musicxml_to_score_document(
                source_path.read_text(encoding="utf-8"),
                source=f"{manifest.get('host_id', 'musicxml')}_bridge",
            )
        return {
            "session": manifest,
            "score_document": score_document,
            "operation_history": {"done": [], "undone": []},
        }

    def get_artifact(self, session_id: str, revision: int) -> dict[str, Any]:
        """Return one MusicXML artifact after validating its session-local path."""

        manifest = self.get_session(session_id)
        wanted_revision = int(revision)
        artifact = next(
            (item for item in manifest.get("artifacts", []) if int(item.get("revision", -1)) == wanted_revision),
            None,
        )
        if artifact is None:
            raise FileNotFoundError(f"Notation bridge revision {wanted_revision} was not found for '{session_id}'.")
        session_dir = self._session_dir(session_id).resolve()
        artifact_path = Path(str(artifact.get("path", ""))).resolve()
        if session_dir not in artifact_path.parents:
            raise ValueError("Notation bridge artifact resolved outside its session directory.")
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Notation bridge artifact is missing: {artifact_path.name}")
        return {
            "session_id": session_id,
            "revision": wanted_revision,
            "filename": artifact_path.name,
            "path": str(artifact_path),
            "sha256": artifact.get("sha256", ""),
            "musicxml": artifact_path.read_text(encoding="utf-8"),
        }

    def export_revision(
        self,
        session_id: str,
        score_document: dict[str, Any],
        expected_revision: int,
    ) -> dict[str, Any]:
        """Export a new MusicXML revision without overwriting prior artifacts."""

        manifest = self.get_session(session_id)
        current_revision = int(manifest.get("revision", 0))
        if int(expected_revision) != current_revision:
            raise NotationBridgeRevisionConflict(
                f"Revision conflict for '{session_id}': expected {expected_revision}, current {current_revision}. Reload before exporting."
            )
        adapter = adapter_for(str(manifest.get("host_id", "musicxml")))
        base_artifact = self.get_artifact(session_id, current_revision)
        before_score = musicxml_to_score_document(
            str(base_artifact["musicxml"]),
            source=f"{manifest.get('host_id', 'musicxml')}_bridge",
        )
        source_patch = patch_musicxml_preserving_source(
            str(base_artifact["musicxml"]),
            before_score,
            score_document,
        )
        musicxml = str(source_patch["musicxml"])
        validation = self.validator.validate_text(musicxml).to_report()
        if not validation.get("valid_musicxml"):
            raise ValueError(f"MusicXML export validation failed: {validation.get('errors', [])}")
        next_revision = current_revision + 1
        session_dir = self._session_dir(session_id)
        output_path = session_dir / adapter.revision_filename(session_id, next_revision)
        if output_path.exists():
            raise FileExistsError(f"Refusing to overwrite existing notation revision: {output_path}")
        output_path.write_text(musicxml, encoding="utf-8")
        digest = _sha256_text(musicxml)
        manifest["revision"] = next_revision
        manifest["current_sha256"] = digest
        manifest["updated_at"] = datetime.now(UTC).isoformat()
        manifest.setdefault("artifacts", []).append(
            {
                "revision": next_revision,
                "kind": "edited_musicxml",
                "path": str(output_path.resolve()),
                "sha256": digest,
                "export_mode": source_patch["export_mode"],
                "changed_event_count": source_patch["changed_event_count"],
                "changed_fields": source_patch["changed_fields"],
                "changed_global_fields": source_patch["changed_global_fields"],
            }
        )
        self._write_json(session_dir / "score_document.json", score_document)
        self._write_manifest(session_dir, manifest)
        return {
            "session": manifest,
            "revision": next_revision,
            "musicxml": musicxml,
            "output_path": str(output_path.resolve()),
            "export_mode": source_patch["export_mode"],
            "source_preservation": {
                "changed_event_count": source_patch["changed_event_count"],
                "changed_event_ids": source_patch["changed_event_ids"],
                "changed_fields": source_patch["changed_fields"],
                "changed_top_level_fields": source_patch["changed_top_level_fields"],
                "changed_global_fields": source_patch["changed_global_fields"],
            },
            "validation_report": validation,
            "handoff": {
                "host_id": adapter.host_id,
                "mode": adapter.capabilities().exchange_mode,
                "steps": list(adapter.capabilities().handoff_steps),
            },
        }

    def _session_dir(self, session_id: str) -> Path:
        if not re.fullmatch(r"bridge_[A-Za-z0-9_-]{8,80}", str(session_id or "")):
            raise ValueError("Invalid notation bridge session id.")
        path = (self.storage_root / session_id).resolve()
        root = self.storage_root.resolve()
        if root != path and root not in path.parents:
            raise ValueError("Notation bridge session resolved outside the storage root.")
        return path

    @staticmethod
    def _write_manifest(session_dir: Path, manifest: dict[str, Any]) -> None:
        manifest_path = session_dir / "manifest.json"
        temporary = session_dir / "manifest.json.tmp"
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(manifest_path)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_host_context(value: dict[str, Any] | None) -> dict[str, Any]:
    """Keep small JSON-compatible host metadata out of executable bridge state."""

    if not value:
        return {}
    encoded = json.dumps(value, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 32_768:
        raise ValueError("Notation host context exceeds the 32 KiB limit.")
    decoded = json.loads(encoded)
    if not isinstance(decoded, dict):
        raise ValueError("Notation host context must be a JSON object.")
    return decoded

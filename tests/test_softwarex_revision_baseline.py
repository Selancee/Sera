import hashlib
import json
from pathlib import Path

from scripts.verify_softwarex_revision_baseline import verify_baseline


def make_baseline(tmp_path: Path) -> Path:
    content = b"Original submission manuscript.\n"
    (tmp_path / "original.md").write_bytes(content)
    manifest = {
        "schema_version": 1,
        "baseline_id": "test-submission",
        "files": [{
            "path": "original.md", "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }],
        "local_archives": [{
            "path": "missing-local-archive.zip", "bytes": 0,
            "sha256": hashlib.sha256(b"").hexdigest(),
        }],
    }
    target = tmp_path / "manifest.json"
    target.write_text(json.dumps(manifest), encoding="utf-8")
    return target


def test_revision_draft_does_not_change_frozen_baseline(tmp_path: Path):
    manifest = make_baseline(tmp_path)
    (tmp_path / "revision.md").write_text("Revised manuscript.", encoding="utf-8")
    assert verify_baseline(manifest, root=tmp_path)["passed"]


def test_silent_baseline_edit_is_detected_even_with_same_size(tmp_path: Path):
    manifest = make_baseline(tmp_path)
    original = tmp_path / "original.md"
    original.write_bytes(original.read_bytes().replace(b"Original", b"Modified"))
    result = verify_baseline(manifest, root=tmp_path)
    assert not result["passed"]
    assert any("SHA-256 mismatch" in error for error in result["errors"])


def test_missing_local_archives_are_required_only_when_requested(tmp_path: Path):
    manifest = make_baseline(tmp_path)
    result = verify_baseline(manifest, root=tmp_path, include_local_archives=True)
    assert not result["passed"]
    assert any("missing-local-archive.zip" in error for error in result["errors"])


def test_manifest_cannot_escape_frozen_directory(tmp_path: Path):
    manifest = make_baseline(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["files"][0]["path"] = "../outside.md"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = verify_baseline(manifest, root=tmp_path)
    assert not result["passed"]
    assert any("path escapes baseline" in error for error in result["errors"])

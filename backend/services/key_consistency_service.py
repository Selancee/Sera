"""Key consistency reporting for generation metadata and debug panels."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from backend.services.score_metadata_sync_service import extract_title_key, keys_equivalent


MAJOR_FIFTHS = {
    0: "C",
    1: "G",
    2: "D",
    3: "A",
    4: "E",
    5: "B",
    6: "F#",
    -1: "F",
    -2: "Bb",
    -3: "Eb",
    -4: "Ab",
    -5: "Db",
}


class KeyConsistencyService:
    """Build a frontend-friendly report across prompt, controls, score, XML, and title."""

    def build_report(
        self,
        intent: dict[str, Any] | None = None,
        resolved_controls: dict[str, Any] | None = None,
        score_document: dict[str, Any] | None = None,
        musicxml: str = "",
        metadata_sync_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        intent = intent or {}
        resolved_controls = resolved_controls or {}
        score_document = score_document or {}
        metadata_sync_report = metadata_sync_report or {}
        prompt_key = str(metadata_sync_report.get("prompt_key") or _prompt_key(intent) or "")
        ui_key = str(metadata_sync_report.get("ui_key") or _ui_key(intent, resolved_controls) or "")
        resolved_key = str(metadata_sync_report.get("resolved_key") or resolved_controls.get("key") or intent.get("key") or "")
        intent_key = str(intent.get("key") or resolved_key or "")
        score_document_key = str((score_document.get("global") or {}).get("key") or "")
        musicxml_key = _musicxml_key(musicxml)
        title = str(score_document.get("title") or intent.get("title") or "")
        title_key = extract_title_key(title) or None

        warnings: list[str] = []
        errors: list[str] = []
        final_key = resolved_key or score_document_key or intent_key
        stale_key_in_title = bool(title_key and final_key and not keys_equivalent(title_key, final_key))
        for label, key in {
            "intent_key": intent_key,
            "score_document_key": score_document_key,
            "musicxml_key": musicxml_key,
        }.items():
            if final_key and key and not keys_equivalent(final_key, key):
                errors.append(f"{label} differs from resolved key {final_key}: {key}")
        if stale_key_in_title:
            warnings.append(f"Title references {title_key}, but resolved score key is {final_key}.")
        if prompt_key and ui_key and not keys_equivalent(prompt_key, ui_key):
            warnings.append("Prompt key and UI key differed; resolved key was used for final score metadata.")

        return {
            "valid": not errors and not stale_key_in_title,
            "prompt_key": prompt_key,
            "ui_key": ui_key,
            "resolved_key": resolved_key,
            "intent_key": intent_key,
            "score_document_key": score_document_key,
            "musicxml_key": musicxml_key,
            "title_key": title_key,
            "stale_key_in_title": stale_key_in_title,
            "warnings": warnings,
            "errors": errors,
        }


def build_key_consistency_report(
    intent: dict[str, Any] | None = None,
    resolved_controls: dict[str, Any] | None = None,
    score_document: dict[str, Any] | None = None,
    musicxml: str = "",
    metadata_sync_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return KeyConsistencyService().build_report(intent, resolved_controls, score_document, musicxml, metadata_sync_report)


def _prompt_key(intent: dict[str, Any]) -> str:
    for conflict in intent.get("prompt_ui_conflicts") or []:
        if conflict.get("field") == "key":
            return str(conflict.get("prompt_value") or "")
    for term in intent.get("prompt_terms") or []:
        if term.get("category") == "key":
            return str(term.get("normalized") or "")
    return ""


def _ui_key(intent: dict[str, Any], resolved_controls: dict[str, Any]) -> str:
    for conflict in intent.get("prompt_ui_conflicts") or []:
        if conflict.get("field") == "key":
            return str(conflict.get("ui_value") or "")
    controls = intent.get("ui_controls") or {}
    return str(controls.get("key") or resolved_controls.get("key") or "")


def _musicxml_key(musicxml: str) -> str:
    if not musicxml:
        return ""
    try:
        root = ET.fromstring(musicxml)
    except ET.ParseError:
        return ""
    attr = root.find(".//attributes")
    if attr is None:
        return ""
    fifths_node = attr.find("./key/fifths")
    mode = (attr.findtext("./key/mode") or "major").strip().lower()
    try:
        fifths = int(float(fifths_node.text or "0")) if fifths_node is not None else 0
    except ValueError:
        fifths = 0
    if mode == "minor":
        tonic = MAJOR_FIFTHS.get(fifths + 3, "A")
        return f"{tonic} minor"
    return f"{MAJOR_FIFTHS.get(fifths, 'C')} major"

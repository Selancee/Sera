"""Synchronize ScoreDocument metadata after final generation controls resolve."""

from __future__ import annotations

import copy
import re
from html import escape
from typing import Any


KEY_PATTERN = re.compile(r"\b([A-G](?:#|b|-flat)?)(?:\s+|-)(major|minor|maj|min)\b", re.IGNORECASE)
WORK_TITLE_PATTERN = re.compile(r"<work-title>.*?</work-title>", re.IGNORECASE | re.DOTALL)
SCORE_PARTWISE_OPEN_PATTERN = re.compile(r"(<score-partwise\b[^>]*>)", re.IGNORECASE)
CREATOR_PATTERN = re.compile(r"<creator\s+type=[\"']composer[\"']>.*?</creator>", re.IGNORECASE | re.DOTALL)


def sync_score_metadata_after_resolution(
    intent: dict[str, Any],
    resolved_controls: dict[str, Any],
    score_document: dict[str, Any],
    musicxml: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return intent, score document, and optional MusicXML with final metadata.

    The prompt-understanding title is provisional until prompt/UI controls have
    been resolved. This service keeps the final ScoreDocument, metadata, and
    MusicXML work title from leaking an earlier prompt key.
    """

    options = dict(options or {})
    synced_intent = copy.deepcopy(intent or {})
    synced_score = copy.deepcopy(score_document or {})
    metadata = synced_score.setdefault("metadata", {})
    resolved = dict(resolved_controls or {})

    title_before = str(synced_score.get("title") or synced_intent.get("title") or "").strip()
    composer_before = str(synced_score.get("composer") or synced_intent.get("composer") or "").strip()
    prompt_key = _prompt_key(synced_intent, options)
    ui_key = _ui_key(synced_intent, resolved, options)
    resolved_key = _clean_key(resolved.get("key") or options.get("resolved_key") or synced_intent.get("key"))
    score_key = _clean_key((synced_score.get("global") or {}).get("key") or resolved_key)
    final_key = _clean_key(resolved_key or score_key or synced_intent.get("key") or "C major")
    title_key_before = _extract_title_key(title_before)
    has_key_conflict = bool(prompt_key and ui_key and not _keys_equivalent(prompt_key, ui_key))
    title_source_before = str(metadata.get("title_source") or synced_intent.get("title_source") or "provisional_agent")

    title_after = title_before or _neutral_title(synced_intent, synced_score)
    title_sync_status = "ok"
    stale_key_removed = False
    if title_key_before and final_key and not _keys_equivalent(title_key_before, final_key):
        stale_key_removed = True
        if has_key_conflict or title_source_before != "user":
            title_after = _neutral_title(synced_intent, synced_score)
            title_sync_status = "neutralized"
        else:
            title_after = _replace_title_key(title_after, final_key)
            title_sync_status = "updated"
    elif not title_before:
        title_sync_status = "updated"
    elif title_key_before and final_key and _keys_equivalent(title_key_before, final_key):
        title_after = _replace_title_key(title_after, final_key)

    composer_after = composer_before or str(resolved.get("composer") or options.get("composer") or "Sera")
    if not composer_after.strip():
        composer_after = "Sera"

    synced_score["title"] = title_after
    synced_score["composer"] = composer_after
    synced_score.setdefault("global", {})["key"] = final_key
    synced_intent["title"] = title_after
    synced_intent["key"] = final_key

    title_key_after = _extract_title_key(title_after)
    title_source = "neutralized" if title_sync_status == "neutralized" else "synchronized" if title_sync_status == "updated" else title_source_before
    metadata.update(
        {
            "title": title_after,
            "composer": composer_after,
            "title_source": title_source,
            "title_contains_key": bool(title_key_after),
            "title_key": title_key_after,
            "title_sync_status": title_sync_status,
        }
    )
    generation_metadata = metadata.setdefault("generation_metadata", {})
    generation_metadata.update(
        {
            "title_source": title_source,
            "title_contains_key": bool(title_key_after),
            "title_key": title_key_after,
            "title_sync_status": title_sync_status,
        }
    )

    synced_musicxml = update_musicxml_metadata(musicxml, title_after, composer_after) if musicxml else (musicxml or "")
    report = {
        "title_before": title_before,
        "title_after": title_after,
        "composer_before": composer_before,
        "composer_after": composer_after,
        "prompt_key": prompt_key,
        "ui_key": ui_key,
        "resolved_key": final_key,
        "score_key": synced_score.get("global", {}).get("key", ""),
        "title_key_before": title_key_before,
        "title_key_after": title_key_after,
        "stale_key_removed": stale_key_removed,
        "work_title_updated": bool(title_after),
        "creator_updated": bool(composer_after),
        "title_source": title_source,
        "title_contains_key": bool(title_key_after),
        "title_sync_status": title_sync_status,
        "warnings": [],
        "errors": [],
    }
    generation_metadata["metadata_sync_report"] = report
    return {
        "intent": synced_intent,
        "score_document": synced_score,
        "musicxml": synced_musicxml,
        "metadata_sync_report": report,
    }


def update_musicxml_metadata(musicxml: str | None, title: str, composer: str) -> str:
    """Patch MusicXML work title and composer while preserving the document."""

    if not musicxml:
        return ""
    title_xml = f"<work-title>{escape(str(title or 'Untitled Sera Score'))}</work-title>"
    creator_xml = f"<creator type=\"composer\">{escape(str(composer or 'Sera'))}</creator>"
    updated = WORK_TITLE_PATTERN.sub(title_xml, musicxml, count=1)
    if updated == musicxml:
        updated = SCORE_PARTWISE_OPEN_PATTERN.sub(rf"\1\n  <work>\n    {title_xml}\n  </work>", updated, count=1)
    if CREATOR_PATTERN.search(updated):
        updated = CREATOR_PATTERN.sub(creator_xml, updated, count=1)
    elif "</identification>" in updated:
        updated = updated.replace("</identification>", f"    {creator_xml}\n  </identification>", 1)
    elif "<part-list>" in updated:
        updated = updated.replace("<part-list>", f"<identification>\n    {creator_xml}\n  </identification>\n  <part-list>", 1)
    return updated


def extract_title_key(title: str) -> str:
    """Public helper used by key consistency checks."""

    return _extract_title_key(title)


def keys_equivalent(left: str, right: str) -> bool:
    """Public helper used by tests and key reports."""

    return _keys_equivalent(left, right)


def _prompt_key(intent: dict[str, Any], options: dict[str, Any]) -> str:
    if options.get("prompt_key"):
        return _clean_key(options["prompt_key"])
    for conflict in intent.get("prompt_ui_conflicts") or []:
        if conflict.get("field") == "key":
            return _clean_key(conflict.get("prompt_value"))
    for term in intent.get("prompt_terms") or []:
        if term.get("category") == "key":
            return _clean_key(term.get("normalized"))
    return ""


def _ui_key(intent: dict[str, Any], resolved: dict[str, Any], options: dict[str, Any]) -> str:
    if options.get("ui_key"):
        return _clean_key(options["ui_key"])
    for conflict in intent.get("prompt_ui_conflicts") or []:
        if conflict.get("field") == "key":
            return _clean_key(conflict.get("ui_value"))
    controls = dict(intent.get("ui_controls") or {})
    return _clean_key(controls.get("key") or resolved.get("key"))


def _extract_title_key(title: str) -> str:
    match = KEY_PATTERN.search(str(title or ""))
    if not match:
        return ""
    tonic = match.group(1).replace("-flat", "b")
    mode = "major" if match.group(2).lower() in {"major", "maj"} else "minor"
    return f"{tonic.upper() if len(tonic) == 1 else tonic[0].upper() + tonic[1:]} {mode}"


def _replace_title_key(title: str, final_key: str) -> str:
    return KEY_PATTERN.sub(str(final_key), str(title), count=1)


def _neutral_title(intent: dict[str, Any], score_document: dict[str, Any]) -> str:
    instruments = list(intent.get("instruments") or intent.get("instrumentation") or [])
    if not instruments:
        for part in score_document.get("parts") or []:
            instrument = part.get("instrument") or part.get("name")
            if instrument:
                instruments.append(str(instrument))
    return "Sera Piano Sketch" if any("piano" in str(item).lower() for item in instruments) else "Sera Sketch"


def _clean_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("-flat", "b")
    match = KEY_PATTERN.search(text)
    if match:
        tonic = match.group(1).replace("-flat", "b")
        mode = "major" if match.group(2).lower() in {"major", "maj"} else "minor"
        return f"{tonic.upper() if len(tonic) == 1 else tonic[0].upper() + tonic[1:]} {mode}"
    parts = text.split()
    if len(parts) >= 2 and parts[1].lower() in {"major", "minor"}:
        tonic = parts[0].replace("-flat", "b")
        return f"{tonic.upper() if len(tonic) == 1 else tonic[0].upper() + tonic[1:]} {parts[1].lower()}"
    return text


def _keys_equivalent(left: str, right: str) -> bool:
    return _clean_key(left).lower().replace("-flat", "b") == _clean_key(right).lower().replace("-flat", "b")

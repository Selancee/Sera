"""Resolve raw prompt intent against structured UI controls."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.services.prompt_term_extractor import extract_prompt_terms


FRONTEND_DEFAULT_CONTROLS = {
    "style": "romantic",
    "instrument": "piano",
    "key": "A minor",
    "meter": "4/4",
    "tempo": 84,
    "length": 16,
    "length_measures": 16,
    "difficulty": "intermediate",
    "rhythmic_density": "medium",
    "texture": "melody_accompaniment",
    "accompaniment_style": "bass_chord",
    "cadence_strength": "clear",
}

CONTROL_ALIASES = {
    "instrument": "instrumentation",
    "length": "length_measures",
}


class PromptControlResolver:
    """Apply prompt-priority conflict rules to generation controls."""

    def resolve(
        self,
        raw_prompt: str,
        ui_controls: dict[str, Any] | None = None,
        control_policy: dict[str, Any] | None = None,
        ui_control_sources: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        controls = _normalize_controls(ui_controls or {})
        sources = dict(ui_control_sources or {})
        policy = {
            "prompt_priority": True,
            "show_conflicts": True,
            "allow_ui_defaults": True,
            **dict(control_policy or {}),
        }
        terms_payload = extract_prompt_terms(raw_prompt)
        prompt_values = _prompt_values_from_terms(terms_payload["prompt_terms"])
        resolved: dict[str, Any] = {}
        conflicts: list[dict[str, Any]] = []
        defaults_used: list[str] = []
        warnings: list[str] = []
        source_control_terms: list[dict[str, Any]] = []

        for field, value in controls.items():
            normalized_field = CONTROL_ALIASES.get(field, field)
            if normalized_field in {"generator_mode", "model_task_type"}:
                continue
            source = sources.get(field) or sources.get(normalized_field) or _infer_source(field, value)
            source_control_terms.append(
                {
                    "field": normalized_field,
                    "value": value,
                    "source": source,
                    "term": f"{normalized_field}={value}",
                }
            )
            prompt_value = prompt_values.get(normalized_field)
            if prompt_value is not None and not _equivalent(prompt_value, value, normalized_field):
                resolution = _conflict_resolution(policy, source)
                conflicts.append(
                    {
                        "field": normalized_field,
                        "prompt_value": prompt_value,
                        "ui_value": value,
                        "ui_source": source,
                        "resolution": resolution,
                        "reason": _conflict_reason(normalized_field, prompt_value, source, resolution),
                    }
                )
                if resolution == "ui_wins":
                    resolved[normalized_field] = value
                else:
                    resolved[normalized_field] = prompt_value
                continue
            if source == "default":
                defaults_used.append(normalized_field)
                if not policy["allow_ui_defaults"]:
                    continue
            resolved[normalized_field] = value

        for field, prompt_value in prompt_values.items():
            resolved.setdefault(field, prompt_value)

        if conflicts and policy["prompt_priority"]:
            if any(item["resolution"] == "ui_wins" for item in conflicts):
                warnings.append("Explicit UI controls conflicted with raw prompt; explicit UI values were preserved.")
            if any(item["resolution"] == "prompt_wins" for item in conflicts):
                warnings.append("Default UI controls conflicted with raw prompt; prompt values were preserved.")

        has_prompt = bool(str(raw_prompt or "").strip())
        has_controls = bool(source_control_terms)
        intent_source = "prompt_plus_controls" if has_prompt and has_controls else "control_only_intent" if has_controls else "raw_prompt"
        return {
            "raw_prompt": raw_prompt,
            "ui_controls": deepcopy(ui_controls or {}),
            "ui_control_sources": sources,
            "resolved_controls": resolved,
            "intent_source": intent_source,
            "control_only_intent": intent_source == "control_only_intent",
            "source_control_terms": source_control_terms,
            "conflicts": conflicts,
            "defaults_used": sorted(set(defaults_used)),
            "prompt_priority_applied": bool(policy["prompt_priority"]),
            "warnings": warnings,
            "prompt_terms": terms_payload["prompt_terms"],
            "source_prompt_terms": terms_payload["source_prompt_terms"],
            "unparsed_prompt_terms": terms_payload["unparsed_prompt_terms"],
            "language": terms_payload["language"],
        }


def resolve_prompt_controls(
    raw_prompt: str,
    ui_controls: dict[str, Any] | None = None,
    control_policy: dict[str, Any] | None = None,
    ui_control_sources: dict[str, str] | None = None,
) -> dict[str, Any]:
    return PromptControlResolver().resolve(raw_prompt, ui_controls, control_policy, ui_control_sources)


def _normalize_controls(controls: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in controls.items():
        if value in {"", None} or key.startswith("_"):
            continue
        normalized[str(key)] = value
    return normalized


def _infer_source(field: str, value: Any) -> str:
    default = FRONTEND_DEFAULT_CONTROLS.get(field)
    if default is None and field == "length_measures":
        default = FRONTEND_DEFAULT_CONTROLS["length"]
    return "default" if str(default) == str(value) else "explicit"


def _conflict_resolution(policy: dict[str, Any], source: str) -> str:
    if source == "explicit":
        return "ui_wins"
    return "prompt_wins" if policy["prompt_priority"] else "ui_wins"


def _conflict_reason(field: str, prompt_value: Any, source: str, resolution: str) -> str:
    if resolution == "ui_wins" and source == "explicit":
        return f"User explicitly selected a UI value for {field}; explicit UI selection overrides prompt value {prompt_value}."
    if resolution == "ui_wins":
        return f"UI control policy selected the UI value for {field}."
    return f"Raw prompt explicitly requested {prompt_value} for {field}."


def _prompt_values_from_terms(terms: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    styles = [str(term["normalized"]) for term in terms if term.get("category") == "style"]
    if styles:
        style_value = _style_value(styles)
        values["style"] = style_value
        if style_value == "cyberpunk":
            values.setdefault("texture", "ostinato")
            values.setdefault("accompaniment_style", "repeating_bass")
            values.setdefault("rhythmic_density", "high")
            values.setdefault("syncopation", "medium_high")
        elif style_value == "chinese":
            values.setdefault("texture", "pentatonic_open_texture")
            values.setdefault("accompaniment_style", "open_fifth_pedal")
    moods = [str(term["normalized"]) for term in terms if term.get("category") == "mood"]
    if moods:
        values["mood"] = moods[0]
    textures = [str(term["normalized"]) for term in terms if term.get("category") == "texture"]
    if textures:
        values["texture"] = "ostinato" if "ostinato" in textures else textures[0]
    rhythms = [str(term["normalized"]) for term in terms if term.get("category") == "rhythm"]
    if "syncopation" in rhythms:
        values["rhythmic_density"] = "high"
        values["syncopation"] = "medium_high"
    if "dotted" in rhythms:
        values["requires_dotted_rhythm"] = True
    accompaniments = [str(term["normalized"]) for term in terms if term.get("category") == "accompaniment"]
    if "repeating_bass" in accompaniments:
        values["accompaniment_style"] = "repeating_bass"
    instruments = [str(term["normalized"]) for term in terms if term.get("category") == "instrumentation"]
    if instruments:
        values["instrumentation"] = instruments[0]
    meters = [str(term["normalized"]) for term in terms if term.get("category") == "meter"]
    if meters:
        values["meter"] = "3/4" if "waltz" in meters else meters[0]
    keys = [str(term["normalized"]) for term in terms if term.get("category") == "key"]
    if keys:
        values["key"] = keys[0]
    lengths = [str(term["normalized"]) for term in terms if term.get("category") == "length"]
    if lengths:
        try:
            values["length_measures"] = int(lengths[0])
        except ValueError:
            pass
    return values


def _style_value(styles: list[str]) -> str:
    if any(style in styles for style in {"cyberpunk", "dark_electronic"}):
        return "cyberpunk"
    if "anime" in styles:
        return "anime"
    if "game" in styles:
        return "game"
    if "cinematic" in styles:
        return "cinematic"
    if "new_age" in styles or "ambient" in styles:
        return "new_age"
    if "chinese" in styles or "pentatonic" in styles or "wuxia" in styles or "xianxia" in styles:
        return "chinese"
    if "electronic" in styles:
        return "electronic"
    return styles[0]


def _equivalent(prompt_value: Any, ui_value: Any, field: str) -> bool:
    if field == "style" and str(prompt_value) == "cyberpunk" and str(ui_value) == "electronic":
        return True
    if field == "length_measures":
        try:
            return int(prompt_value) == int(ui_value)
        except (TypeError, ValueError):
            return False
    return str(prompt_value).replace("_", "-").lower() == str(ui_value).replace("_", "-").lower()

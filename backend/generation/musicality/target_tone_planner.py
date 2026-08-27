"""Harmonic target-tone planning for V0.96.2 phrase melodies."""

from __future__ import annotations

from typing import Any


STEP_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def plan_target_tones(
    harmony_plan: list[Any],
    phrase_role: str,
    style_profile: dict[str, Any],
    melodic_style_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return preferred pitch classes for strong beats and phrase endings."""

    family = _style_family(style_profile, melodic_style_profile)
    key = str((style_profile or {}).get("key") or (melodic_style_profile or {}).get("key") or "C major")
    tonic = _key_tonic_pc(key)
    targets: list[dict[str, Any]] = []
    for index, chord in enumerate(harmony_plan or ["I"], start=1):
        chord_text = str(chord.get("chord") if isinstance(chord, dict) else chord)
        pcs = _target_pcs_for_style(chord_text, tonic, family, phrase_role, index == len(harmony_plan))
        target_type = _target_type_for_style(family, phrase_role, index == len(harmony_plan))
        targets.append(
            {
                "measure": int(chord.get("measure", index) if isinstance(chord, dict) else index),
                "beat": 1,
                "target_type": target_type,
                "preferred_pitch_classes": sorted({int(pc) % 12 for pc in pcs}),
                "required": bool(index == len(harmony_plan) or index % 4 == 0 or phrase_role in {"cadence", "final", "consequent"}),
                "source": "harmony_profile",
                "chord": chord_text,
                "style_family": family,
            }
        )
    return targets


def target_tone_hit_report(melody_events: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure target-tone hits on strong beats and phrase endings."""

    target_by_measure = {int(item.get("measure", 0) or 0): item for item in targets}
    checks = []
    required_checks = []
    for event in melody_events:
        if event.get("type") == "rest" or event.get("midi") is None:
            continue
        measure = int(event.get("measure", 0) or 0)
        target = target_by_measure.get(measure)
        if not target:
            continue
        strong = abs(float(event.get("offset", 0.0) or 0.0) - round(float(event.get("offset", 0.0) or 0.0))) < 0.01
        phrase_end = bool(event.get("phrase_end"))
        if not strong and not phrase_end:
            continue
        pcs = {int(pc) % 12 for pc in target.get("preferred_pitch_classes", [])}
        hit = int(event.get("midi", 0)) % 12 in pcs
        checks.append(hit)
        if target.get("required") or phrase_end:
            required_checks.append(hit)
    hit_rate = sum(1 for item in checks if item) / max(1, len(checks))
    required_rate = sum(1 for item in required_checks if item) / max(1, len(required_checks))
    return {
        "engine": "target_tone_planner_v0962",
        "target_tone_hit_rate": round(hit_rate, 4),
        "required_target_tone_hit_rate": round(required_rate, 4),
        "checked_target_count": len(checks),
    }


def _target_pcs_for_style(chord: str, tonic: int, family: str, phrase_role: str, final_measure: bool) -> list[int]:
    chord_pcs = _roman_chord_pcs(chord, tonic)
    if final_measure or phrase_role in {"cadence", "final", "consequent"}:
        if family == "jazz":
            return [tonic, (tonic + 4) % 12, (tonic + 10) % 12]
        if family == "chinese":
            return [tonic, (tonic + 7) % 12]
        if family == "cyberpunk":
            return [tonic, (tonic + 3) % 12, (tonic + 10) % 12]
        return [tonic, (tonic + 7) % 12]
    if family == "jazz":
        return chord_pcs[1:] + [(chord_pcs[0] + 10) % 12, (chord_pcs[0] + 2) % 12]
    if family == "pop":
        return [tonic, (tonic + 4) % 12, (tonic + 7) % 12, (tonic + 9) % 12]
    if family == "chinese":
        return [tonic, (tonic + 2) % 12, (tonic + 4) % 12, (tonic + 7) % 12, (tonic + 9) % 12]
    if family == "cyberpunk":
        return [tonic, (tonic + 3) % 12, (tonic + 7) % 12, (tonic + 10) % 12]
    return chord_pcs


def _target_type_for_style(family: str, phrase_role: str, final_measure: bool) -> str:
    if final_measure or phrase_role in {"cadence", "final", "consequent"}:
        return "cadence_tone" if family != "chinese" else "pentatonic_center"
    return {
        "jazz": "chord_3rd_or_7th",
        "pop": "hook_tone",
        "classical": "chord_tone",
        "romantic": "delayed_resolution_tone",
        "chinese": "pentatonic_center",
        "cyberpunk": "modal_tension_tone",
    }.get(family, "chord_tone")


def _roman_chord_pcs(chord: str, tonic: int) -> list[int]:
    clean = str(chord or "I").replace("maj9", "").replace("maj7", "").replace("alt", "").replace("7", "")
    degree_roots = {
        "I": 0,
        "i": 0,
        "ii": 2,
        "iii": 4,
        "III": 3,
        "IV": 5,
        "iv": 5,
        "V": 7,
        "v": 7,
        "vi": 9,
        "VI": 8,
        "VII": 10,
    }
    root = (tonic + degree_roots.get(clean, 0)) % 12
    minorish = clean.islower() or clean in {"i", "iv", "VI", "VII", "III"}
    third = 3 if minorish else 4
    return [root, (root + third) % 12, (root + 7) % 12]


def _key_tonic_pc(key: str) -> int:
    token = str(key or "C").split()[0].replace("-flat", "b")
    if not token:
        return 0
    step = token[0].upper()
    alter = 0
    if len(token) > 1:
        if token[1] == "#":
            alter = 1
        elif token[1].lower() == "b":
            alter = -1
    return (STEP_TO_PC.get(step, 0) + alter) % 12


def _style_family(style_profile: dict[str, Any], melodic_style_profile: dict[str, Any]) -> str:
    tags = {str(item).lower() for item in (style_profile or {}).get("custom_style_tags", [])}
    family = str((melodic_style_profile or {}).get("style_family") or (style_profile or {}).get("base_style") or (style_profile or {}).get("style") or "classical").lower()
    if "cyberpunk" in tags or family == "electronic":
        return "cyberpunk"
    return family

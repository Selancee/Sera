"""Playable chord voicing helpers for V0.96 harmony profiles."""

from __future__ import annotations

from typing import Any


ROMAN_ROOTS_MAJOR = {"I": 0, "ii": 2, "iii": 4, "IV": 5, "V": 7, "vi": 9, "VII": 10, "bII": 1}
ROMAN_ROOTS_MINOR = {"i": 0, "ii": 2, "III": 3, "iv": 5, "V": 7, "VI": 8, "VII": 10, "bII": 1}
STEP_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def voice_chord(
    chord_symbol: str,
    harmony_profile: dict[str, Any],
    register: str,
    role: str,
    previous_voicing: list[int] | None = None,
) -> dict[str, Any]:
    """Generate a compact playable voicing and metadata."""

    mode = str(harmony_profile.get("mode", "major"))
    root = (_key_tonic_pc(str(harmony_profile.get("key") or "C major")) + _roman_root(chord_symbol, mode)) % 12
    style = str(harmony_profile.get("style", "classical"))
    voicing_style = str(harmony_profile.get("voicing_style", "closed_four_part"))
    base = {"bass": 36, "left_hand": 48, "middle": 60, "right_hand": 64}.get(register, 60)
    if role in {"bass", "left_hand"}:
        base = min(base, 48)
    if voicing_style == "rootless_extended" and style == "jazz":
        intervals = [4, 10, 14, 21] if "7" in chord_symbol else [4, 7, 14, 21]
        rootless = True
    elif voicing_style == "open_fifth_quartal":
        intervals = [0, 7, 14] if "5" in chord_symbol or style == "chinese" else [0, 5, 10]
        rootless = False
    elif voicing_style == "modal_pedal_cluster":
        # V0.96.2 has no dissonance-resolution layer for left-hand clusters yet.
        # Use open fifth/ninth support so modal accompaniment does not collide
        # with a separately generated natural-minor melody by semitone spelling.
        intervals = [0, 7, 14]
        rootless = False
    elif voicing_style == "wide_arpeggiated":
        third = _third_interval(chord_symbol, mode)
        intervals = [0, 7, 10, 12 + third] if _has_dominant_seventh(chord_symbol) else [0, 7, 12, 12 + third]
        rootless = False
    elif voicing_style == "playable_piano_pop":
        third = _third_interval(chord_symbol, mode)
        intervals = [0, 5, 7, 14] if "sus" in chord_symbol else [0, third, 7, 14]
        rootless = False
    else:
        quality = [0, _third_interval(chord_symbol, mode), 7]
        intervals = quality + ([11] if "maj7" in chord_symbol or "maj9" in chord_symbol else [10] if "7" in chord_symbol else [])
        rootless = False
    voicing = [_fit_register(base + root + interval, register) for interval in intervals]
    voicing = _dedupe_voicing(_smooth_from_previous(sorted(set(voicing)), previous_voicing))
    return {
        "chord_symbol": chord_symbol,
        "voicing": voicing,
        "register": register,
        "role": role,
        "voicing_style": voicing_style,
        "rootless": rootless,
        "playability_score": _playability_score(voicing, register),
    }


def _roman_root(symbol: str, mode: str) -> int:
    clean = str(symbol).replace("maj9", "").replace("maj7", "").replace("add9", "").replace("7alt", "").replace("7", "").replace("5", "")
    clean = clean.replace("(add2)", "").replace("(add4)", "")
    if "/" in clean:
        base, target = clean.split("/", 1)
        target_root = _roman_root(target, mode)
        if base in {"V", "v"}:
            return (target_root + 7) % 12
        return target_root
    table = ROMAN_ROOTS_MINOR if mode == "minor" else ROMAN_ROOTS_MAJOR
    return table.get(clean, table.get(clean[:2], table.get(clean[:1], 0)))


def _third_interval(symbol: str, mode: str) -> int:
    clean = str(symbol).replace("maj9", "").replace("maj7", "").replace("add9", "").replace("7alt", "").replace("7", "").replace("5", "")
    clean = clean.replace("(add2)", "").replace("(add4)", "")
    if "/" in clean:
        clean = clean.split("/", 1)[0]
    if "sus" in str(symbol):
        return 5
    if mode == "minor" and clean in {"I", "IV"}:
        return 3
    if clean[:1].islower() or clean in {"i", "iv"}:
        return 3
    if mode == "minor" and clean in {"i", "iv"}:
        return 3
    return 4


def _has_dominant_seventh(symbol: str) -> bool:
    text = str(symbol)
    return "7" in text and "maj7" not in text and "maj9" not in text


def _key_tonic_pc(key: str) -> int:
    token = str(key or "C").split()[0].replace("-flat", "b")
    if not token:
        return 0
    step = token[0].upper()
    alter = 0
    if len(token) > 1:
        accidental = token[1:]
        if accidental.startswith("#"):
            alter = 1
        elif accidental.startswith("b"):
            alter = -1
    return (STEP_TO_PC.get(step, 0) + alter) % 12


def _fit_register(midi: int, register: str) -> int:
    low, high = {
        "bass": (36, 55),
        "left_hand": (40, 64),
        "middle": (52, 76),
        "right_hand": (60, 84),
    }.get(register, (48, 76))
    while midi < low:
        midi += 12
    while midi > high:
        midi -= 12
    return midi


def _smooth_from_previous(voicing: list[int], previous: list[int] | None) -> list[int]:
    if not previous:
        return voicing
    adjusted = []
    for index, pitch in enumerate(voicing):
        target = previous[min(index, len(previous) - 1)]
        options = [pitch - 12, pitch, pitch + 12]
        adjusted.append(min(options, key=lambda item: abs(item - target)))
    return sorted(adjusted)


def _dedupe_voicing(voicing: list[int]) -> list[int]:
    deduped = sorted(set(int(item) for item in voicing))
    return deduped


def _playability_score(voicing: list[int], register: str) -> float:
    if not voicing:
        return 0.0
    span = max(voicing) - min(voicing)
    muddy = register in {"bass", "left_hand"} and any(abs(a - b) <= 2 and min(a, b) < 48 for a in voicing for b in voicing if a != b)
    score = 1.0
    if span > 24:
        score -= 0.25
    if muddy:
        score -= 0.35
    return round(max(0.0, score), 4)

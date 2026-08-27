"""Generate and repair simple melodies with expectation constraints."""

from __future__ import annotations

from typing import Any

from backend.generation.musicality.melody_expectation_validator import validate_melody_expectation

STEP_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def generate_expectation_melody(
    phrase_plan: dict[str, Any],
    harmony_plan: list[Any],
    style_profile: dict[str, Any],
    melodic_style_profile: dict[str, Any],
    rng: Any,
) -> dict[str, Any]:
    """Create a compact phrase melody and validate it."""

    key = str(phrase_plan.get("key") or style_profile.get("key") or "C major")
    count = max(4, int(phrase_plan.get("note_count", 8) or 8))
    tonic_pc = int(phrase_plan.get("tonic_pc", _key_tonic_pc(key)) or 0)
    root = 60 + tonic_pc
    while root < 58:
        root += 12
    while root > 70:
        root -= 12
    style_family = str(melodic_style_profile.get("style_family") or style_profile.get("base_style") or style_profile.get("style") or "classical")
    variant_index = int(phrase_plan.get("variant_index", 0) or 0)
    shapes = _style_shapes(style_family)
    shape = list(shapes[variant_index % len(shapes)])
    if str(phrase_plan.get("contour", "")) == "descending":
        shape = list(reversed(shape))
    phrase_role = str(phrase_plan.get("phrase_role", ""))
    if phrase_role in {"cadence", "final"} and len(shape) >= 2:
        shape[-2:] = [7, 0] if style_family not in {"jazz"} else [10, 4]
    durations = list(phrase_plan.get("durations_quarters") or [])
    if len(durations) < count:
        durations.extend([0.5] * (count - len(durations)))
    events = []
    offset = float(phrase_plan.get("start_offset", 0.0) or 0.0)
    for index in range(count):
        jitter_choices = [0, 0, 0, 12, -12]
        if style_family == "jazz":
            jitter_choices = [0, 0, 0, 1, -1]
        jitter = rng.choice(jitter_choices) if hasattr(rng, "choice") and index not in {0, count - 1} else 0
        pitch = root + shape[index % len(shape)] + jitter
        while pitch < 55:
            pitch += 12
        while pitch > 81:
            pitch -= 12
        duration = float(durations[index])
        events.append({"type": "note", "midi": pitch, "duration": duration, "offset": offset, "measure": int(phrase_plan.get("measure", 1) or 1)})
        offset += duration
    if events:
        events[-1]["duration"] = max(float(events[-1].get("duration", 0.5) or 0.5), 1.0)
    repaired = repair_melody_by_expectation(events, harmony_plan, style_profile, options={"key": key, "force_closure": phrase_role in {"cadence", "final"}})
    return {
        "melody_events": repaired["melody_events"],
        "melody_expectation_report": repaired["melody_expectation_report"],
    }


def repair_melody_by_expectation(
    melody_events: list[dict[str, Any]],
    harmony_context: list[Any],
    style_profile: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply conservative repairs for large leaps, gap fill, and closure."""

    repaired = [dict(event) for event in melody_events]
    repairs: list[str] = []
    for index in range(len(repaired) - 2):
        current = _midi(repaired[index])
        next_pitch = _midi(repaired[index + 1])
        following = _midi(repaired[index + 2])
        if current is None or next_pitch is None or following is None:
            continue
        leap = next_pitch - current
        if abs(leap) > 5:
            target = next_pitch - (2 if leap > 0 else -2)
            if (following - next_pitch) * leap > 0 or abs(following - next_pitch) > 4:
                repaired[index + 2]["midi"] = target
                repaired[index + 2]["pitch"] = _pitch_name(target)
                repairs.append("gap_fill_after_large_leap")
    if repaired and (options or {}).get("force_closure", True):
        key = str((style_profile.get("key") if style_profile else "") or ((options or {}).get("key")) or "C major")
        tonic = 60 + _key_tonic_pc(key)
        while tonic < 58:
            tonic += 12
        while tonic > 70:
            tonic -= 12
        repaired[-1]["midi"] = tonic
        repaired[-1]["pitch"] = _pitch_name(tonic)
        repaired[-1]["duration"] = repaired[-1].get("duration") or "quarter"
        repairs.append("closed_phrase_on_tonic")
    report = validate_melody_expectation(
        repaired,
        harmony_context=harmony_context,
        key=str((options or {}).get("key") or style_profile.get("key") or "C major"),
        style_profile=style_profile,
        options={"repairs_applied": repairs},
    )
    return {"melody_events": repaired, "melody_expectation_report": report}


def _midi(event: dict[str, Any]) -> int | None:
    value = event.get("midi")
    if isinstance(value, int):
        return value
    return None


def _pitch_name(midi: int) -> str:
    steps = {
        0: ("C", ""),
        1: ("C", "#"),
        2: ("D", ""),
        3: ("E", "b"),
        4: ("E", ""),
        5: ("F", ""),
        6: ("F", "#"),
        7: ("G", ""),
        8: ("A", "b"),
        9: ("A", ""),
        10: ("B", "b"),
        11: ("B", ""),
    }
    step, accidental = steps[midi % 12]
    return f"{step}{accidental}{midi // 12 - 1}"


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


def _style_shapes(style_family: str) -> list[list[int]]:
    if style_family == "jazz":
        return [[4, 3, 2, 4, 7, 10, 9, 4], [10, 9, 7, 4, 3, 4, 7, 10], [2, 4, 7, 10, 11, 10, 7, 4]]
    if style_family == "pop":
        return [[0, 4, 7, 4, 9, 7, 4, 0], [7, 9, 7, 4, 2, 4, 2, 0], [0, 7, 9, 7, 4, 2, 0, 0]]
    if style_family == "classical":
        return [[0, 2, 4, 7, 5, 4, 2, 0], [4, 5, 7, 11, 12, 11, 7, 0], [7, 5, 4, 2, 0, 2, 11, 12]]
    if style_family == "chinese":
        return [[0, 2, 4, 7, 9, 7, 4, 2], [7, 9, 7, 4, 2, 0, 2, 4]]
    if style_family == "cyberpunk":
        return [[0, 3, 2, 0, 7, 3, 2, 0], [0, 7, 3, 2, 10, 7, 3, 2]]
    if style_family == "romantic":
        return [[0, 2, 4, 7, 9, 11, 7, 4], [4, 7, 9, 12, 11, 9, 7, 4]]
    return [[0, 2, 4, 7, 5, 4, 2, 0]]

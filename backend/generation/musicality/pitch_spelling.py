"""Key-aware pitch spelling helpers for generated ScoreDocument events."""

from __future__ import annotations


STEP_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
STEPS = ["C", "D", "E", "F", "G", "A", "B"]
MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]


def midi_to_pitch_name(midi: int, key: str = "C major", mode: str | None = None) -> str:
    """Spell a MIDI pitch using the active key instead of a fixed flat/sharp map."""

    midi = int(midi)
    pc = midi % 12
    step, alter = pitch_class_spelling(pc, key, mode)
    octave = midi // 12 - 1
    # Cb/B# style octave crossings are intentionally out of scope for this
    # lightweight generator; generated spellings are restricted to single
    # sharps/flats so MusicXML stays simple and stable.
    accidental = "#" if alter == 1 else "b" if alter == -1 else ""
    return f"{step}{accidental}{octave}"


def pitch_class_spelling(pc: int, key: str = "C major", mode: str | None = None) -> tuple[str, int]:
    """Return a single-accidental spelling for a pitch class in the given key."""

    pc = int(pc) % 12
    tonic_step, tonic_pc = _key_tonic(key)
    mode = (mode or ("minor" if "minor" in str(key).lower() else "major")).lower()
    scale = MINOR_INTERVALS if mode == "minor" else MAJOR_INTERVALS
    spelling_by_pc: dict[int, tuple[str, int]] = {}
    tonic_index = STEPS.index(tonic_step)
    for degree, interval in enumerate(scale):
        step = STEPS[(tonic_index + degree) % 7]
        target_pc = (tonic_pc + interval) % 12
        natural_pc = STEP_TO_PC[step]
        spelling_by_pc[target_pc] = (step, _normalize_alter(target_pc - natural_pc))

    if pc in spelling_by_pc:
        return spelling_by_pc[pc]

    # In minor keys, prefer the raised leading tone spelling, e.g. G# in A minor.
    if mode == "minor" and pc == (tonic_pc + 11) % 12:
        step = STEPS[(tonic_index + 6) % 7]
        return step, _normalize_alter(pc - STEP_TO_PC[step])

    # Common chromatic/modal colors should not be spelled as augmented unisons
    # against the prevailing key. Prefer flat scale-degree spellings for b2,
    # b3, b6, and b7, e.g. Bb rather than A# in C.
    chromatic_degrees = {
        1: 1,   # b2
        3: 2,   # b3
        8: 5,   # b6
        10: 6,  # b7
    }
    relative_pc = (pc - tonic_pc) % 12
    if relative_pc in chromatic_degrees:
        step = STEPS[(tonic_index + chromatic_degrees[relative_pc]) % 7]
        return step, _normalize_alter(pc - STEP_TO_PC[step])

    scale_letters = {step for step, _alter in spelling_by_pc.values()}
    candidates: list[tuple[int, int, str, int]] = []
    for step in STEPS:
        natural_pc = STEP_TO_PC[step]
        for alter in (-1, 0, 1):
            if (natural_pc + alter) % 12 != pc:
                continue
            scale_bias = 0 if step in scale_letters else 1
            candidates.append((abs(alter), scale_bias, step, alter))
    if candidates:
        _, _, step, alter = min(candidates)
        return step, alter

    # Defensive fallback; all 12 pitch classes should be covered above.
    return "C", 0


def _key_tonic(key: str) -> tuple[str, int]:
    token = str(key or "C").split()[0].replace("-flat", "b")
    if not token:
        return "C", 0
    step = token[0].upper()
    alter = 0
    if len(token) > 1:
        accidental = token[1:]
        if accidental.startswith("#"):
            alter = 1
        elif accidental.lower().startswith("b"):
            alter = -1
    return step if step in STEP_TO_PC else "C", (STEP_TO_PC.get(step, 0) + alter) % 12


def _normalize_alter(delta: int) -> int:
    delta = int(delta)
    while delta > 6:
        delta -= 12
    while delta < -6:
        delta += 12
    if delta > 1:
        return 1
    if delta < -1:
        return -1
    return delta

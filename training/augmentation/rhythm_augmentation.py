"""Rhythm augmentation patterns for V0.5 structured events."""

from __future__ import annotations


RHYTHM_PATTERNS = [
    ["RHYTHM_EIGHTH", "RHYTHM_EIGHTH", "RHYTHM_QUARTER", "RHYTHM_QUARTER"],
    ["RHYTHM_QUARTER", "RHYTHM_EIGHTH", "RHYTHM_EIGHTH", "RHYTHM_QUARTER"],
    ["RHYTHM_DOTTED_QUARTER", "RHYTHM_EIGHTH", "RHYTHM_QUARTER"],
    ["RHYTHM_EIGHTH", "RHYTHM_QUARTER", "RHYTHM_EIGHTH", "RHYTHM_QUARTER"],
    ["RHYTHM_QUARTER", "RHYTHM_QUARTER", "RHYTHM_EIGHTH", "RHYTHM_EIGHTH"],
    ["RHYTHM_EIGHTH", "RHYTHM_QUARTER", "RHYTHM_EIGHTH", "RHYTHM_EIGHTH", "RHYTHM_EIGHTH"],
]


def augment_rhythm_events(events: list[str], pattern_index: int = 0) -> tuple[list[str], dict]:
    """Replace overlong quarter runs with a simple varied pattern."""

    pattern = RHYTHM_PATTERNS[pattern_index % len(RHYTHM_PATTERNS)]
    output: list[str] = []
    run = 0
    replacements = 0
    pattern_pos = 0
    for token in events:
        if token == "RHYTHM_QUARTER":
            run += 1
            if run > 2:
                output.append(pattern[pattern_pos % len(pattern)])
                pattern_pos += 1
                replacements += 1
                continue
        elif token.startswith("RHYTHM_"):
            run = 0
        output.append(token)
    return output, {"augmentation": "rhythm", "pattern": " ".join(pattern), "replacements": replacements}

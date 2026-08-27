"""Small, inspectable theory knowledge base for plan retrieval.

The entries are original engineering summaries, not passages copied from books.
They guide planning and deterministic criticism; they are not a claim that one
rule system captures every musical tradition.
"""

from __future__ import annotations

import re

from sera_edit.composer.models import TheoryPrinciple


PRINCIPLES: tuple[TheoryPrinciple, ...] = (
    TheoryPrinciple(
        "TH-SAFE-001",
        "Preserve the host scaffold",
        "When composing inside an imported passage, retain event count, rhythm, instrumentation, and layout unless the host bridge explicitly supports those structural changes.",
        ("safety", "rhythm", "host", "layout"),
        ("theory_variation", "reharmonize", "orchestration_advice"),
    ),
    TheoryPrinciple(
        "TH-HARM-001",
        "Phrase-directed harmony",
        "Use harmonic motion to establish, intensify, and close a phrase; reserve a stable tonic-function arrival for a requested closed ending.",
        ("harmony", "cadence", "phrase", "和声", "终止"),
        ("theory_variation", "reharmonize"),
    ),
    TheoryPrinciple(
        "TH-HARM-002",
        "Chord-tone anchoring",
        "Place structurally important notes on chord tones while allowing scale tones to connect them without changing the rhythmic scaffold.",
        ("melody", "harmony", "chord", "旋律", "和弦"),
        ("theory_variation", "reharmonize"),
    ),
    TheoryPrinciple(
        "TH-VL-001",
        "Economical voice motion",
        "Prefer common tones, stepwise motion, and contrary or oblique motion; treat large leaps and style-inappropriate parallel perfect intervals as review signals.",
        ("voice", "counterpoint", "classical", "声部", "对位"),
        ("theory_variation", "reharmonize"),
    ),
    TheoryPrinciple(
        "TH-MOTIF-001",
        "Motivic economy",
        "Create coherence by repeating or varying a compact interval contour rather than inventing unrelated material in every measure.",
        ("motif", "variation", "minimal", "动机", "发展"),
        ("theory_variation",),
    ),
    TheoryPrinciple(
        "TH-TENSION-001",
        "Auditable tension curve",
        "Plan tension measure by measure and review whether register, harmonic function, and cadence produce the intended rise and release.",
        ("tension", "release", "cinematic", "romantic", "张力"),
        ("theory_variation", "reharmonize"),
    ),
    TheoryPrinciple(
        "TH-PLAY-001",
        "Register and playability",
        "Keep parts in practical registers, avoid unintended voice crossing, and flag repeated leaps larger than an octave.",
        ("playability", "register", "piano", "配器", "音域"),
        ("theory_variation", "reharmonize", "orchestration_advice"),
    ),
    TheoryPrinciple(
        "TH-ORCH-001",
        "Orchestration as role assignment",
        "Describe register, density, doubling, and timbral roles separately from notes; do not silently change host instrumentation when the bridge cannot preserve that change.",
        ("orchestration", "instrumentation", "timbre", "配器", "乐器"),
        ("orchestration_advice",),
    ),
)


def retrieve_theory(brief: str, mode: str, style_family: str, *, limit: int = 6) -> list[dict[str, object]]:
    """Return deterministic, traceable theory context for a composition brief."""

    tokens = set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{1,4}", brief.lower()))
    tokens.update({mode, style_family})
    ranked: list[tuple[int, TheoryPrinciple, str]] = []
    for principle in PRINCIPLES:
        if mode not in principle.applies_to:
            continue
        matches = sorted(token for token in tokens if any(token in tag or tag in token for tag in principle.tags))
        core_bonus = 3 if principle.claim_id in {"TH-SAFE-001", "TH-HARM-001", "TH-PLAY-001"} else 0
        score = core_bonus + len(matches) * 2
        ranked.append((score, principle, ", ".join(matches) if matches else "core rule for selected mode"))
    ranked.sort(key=lambda item: (-item[0], item[1].claim_id))
    return [principle.as_dict(match_reason=reason) for _, principle, reason in ranked[:limit]]

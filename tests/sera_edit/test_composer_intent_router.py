"""Creative intent routing must be explicit and deterministic."""

from __future__ import annotations

import pytest

from sera_edit.composer.intent_router import is_compositional_edit_instruction


@pytest.mark.parametrize(
    "instruction",
    [
        "重写当前选区的旋律，保持节奏不变",
        "为这个主题创作一个变奏",
        "重新和声化左手并保护旋律",
        "Rewrite the melody while preserving rhythm.",
        "Reharmonize these measures in a romantic style.",
    ],
)
def test_routes_explicit_compositional_edits(instruction: str) -> None:
    assert is_compositional_edit_instruction(instruction) is True


@pytest.mark.parametrize(
    "instruction",
    [
        "将旋律升高大二度",
        "把所有音符设为断奏",
        "让它更像海浪",
        "将第三个音设为 F#4",
    ],
)
def test_keeps_atomic_or_vague_edits_out_of_composer(instruction: str) -> None:
    assert is_compositional_edit_instruction(instruction) is False


"""Repository-wide test isolation from developer or user LLM credentials."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_unrequested_live_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep deterministic tests offline unless a test explicitly opts in."""

    monkeypatch.setenv("SERA_LLM_PROVIDER", "mock")

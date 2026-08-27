"""Typed contracts for Sera Composer plans and candidate reviews."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


CompositionMode = Literal["theory_variation", "reharmonize", "orchestration_advice"]
StyleFamily = Literal["classical", "romantic", "jazz", "pop", "minimal", "modal", "cinematic"]


@dataclass(frozen=True, slots=True)
class CompositionPlan:
    """Server-owned high-level plan; an LLM may suggest but cannot widen its scope."""

    schema_version: str
    plan_id: str
    brief: str
    mode: CompositionMode
    style_family: StyleFamily
    key: str
    meter: str
    measures: tuple[int, ...]
    harmonic_progression: tuple[str, ...]
    texture: str
    motif_strategy: str
    tension_curve: tuple[float, ...]
    dynamics_curve: tuple[str, ...]
    preserve_rhythm: bool = True
    preserve_event_count: bool = True
    preserve_instrumentation: bool = True
    preserve_melody: bool = False
    theory_claim_ids: tuple[str, ...] = ()
    style_rule_ids: tuple[str, ...] = ()
    style_knowledge_version: str = "0.4.0"
    knowledge_context_fingerprint: str = ""
    knowledge_token_estimate: int = 0
    orchestration_notes: tuple[str, ...] = ()
    source_fingerprint: str = ""
    target_scope: dict[str, Any] = field(default_factory=dict)
    protected_scope: dict[str, Any] = field(default_factory=dict)
    seed: int = 42

    def as_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        data = asdict(self)
        for key in (
            "measures",
            "harmonic_progression",
            "tension_curve",
            "dynamics_curve",
            "theory_claim_ids",
            "style_rule_ids",
            "orchestration_notes",
        ):
            data[key] = list(data[key])
        return data


@dataclass(frozen=True, slots=True)
class TheoryPrinciple:
    """A concise, original rule summary with a stable evidence identifier."""

    claim_id: str
    title: str
    rule: str
    tags: tuple[str, ...]
    applies_to: tuple[str, ...]
    provenance: str = "sera_curated_theory_summary"

    def as_dict(self, *, match_reason: str = "") -> dict[str, Any]:
        data = asdict(self)
        data["tags"] = list(self.tags)
        data["applies_to"] = list(self.applies_to)
        data["match_reason"] = match_reason
        return data

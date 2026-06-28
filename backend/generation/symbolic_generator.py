"""Generator facade for symbolic score creation."""

from __future__ import annotations

from backend.generation.model_generator import ModelGenerator
from backend.generation.rule_based_generator import GeneratedScore, RuleBasedGenerator
from backend.models.schemas import CompositionPlan


class SymbolicMusicGenerator:
    """Route plans to rule-based or model-backed symbolic generators."""

    def __init__(self, backend: str = "rule_based") -> None:
        self.backend = backend
        self.rule_based = RuleBasedGenerator()
        self.model_generator = ModelGenerator()

    def generate(self, plan: CompositionPlan) -> GeneratedScore:
        """Generate a score using the configured backend.

        The model backend is a stub in this MVP and falls back to the
        rule-based generator unless a future training pipeline registers a
        real symbolic model.
        """

        if self.backend == "model":
            generated = self.model_generator.generate(plan)
            if generated is not None:
                return generated
        return self.rule_based.generate(plan)

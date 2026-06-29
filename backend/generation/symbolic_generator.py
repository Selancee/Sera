"""Generator facade for symbolic score creation."""

from __future__ import annotations

from pathlib import Path

from backend.generation.model_generator import ModelGenerator
from backend.generation.rule_based_generator import GeneratedScore, RuleBasedGenerator
from backend.models.schemas import CompositionPlan


class SymbolicMusicGenerator:
    """Route plans to rule-based or model-backed symbolic generators."""

    def __init__(self, backend: str = "rule_based", project_root: str | Path | None = None) -> None:
        self.backend = backend if backend in {"rule_based", "model"} else "rule_based"
        self.rule_based = RuleBasedGenerator()
        self.model_generator = ModelGenerator(project_root)

    def generate(self, plan: CompositionPlan) -> GeneratedScore:
        """Generate a score using the configured backend.

        TODO: replace the fallback once the small model has a constrained
        MusicXML decoder. Until then, model mode tries the checkpoint path and
        falls back to rule-based output when token output cannot safely become
        a GeneratedScore.
        """

        if self.backend == "model":
            generated = self.model_generator.generate(plan)
            if generated is not None:
                return generated
        return self.rule_based.generate(plan)

"""Generator facade for symbolic score creation."""

from __future__ import annotations

from pathlib import Path

from backend.generation.hybrid_generator import HybridV05Generator
from backend.generation.model_generator import ModelGenerator
from backend.generation.rule_based_generator import GeneratedScore, RuleBasedGenerator
from backend.models.schemas import CompositionPlan


class SymbolicMusicGenerator:
    """Route plans to rule-based or model-backed symbolic generators."""

    def __init__(self, backend: str = "rule_based", project_root: str | Path | None = None) -> None:
        aliases = {"model_based": "model", "hybrid": "hybrid_v05"}
        requested = aliases.get(backend, backend)
        self.backend = requested if requested in {"rule_based", "model", "hybrid_v04", "hybrid_v05", "hybrid_v05_no_postprocess"} else "rule_based"
        self.rule_based = RuleBasedGenerator()
        self.model_generator = ModelGenerator(project_root)
        self.hybrid_v05 = HybridV05Generator(project_root, enable_postprocess=self.backend != "hybrid_v05_no_postprocess")

    def generate(self, plan: CompositionPlan) -> GeneratedScore:
        """Generate a score using the configured backend.

        TODO: replace the fallback once the small model has a constrained
        MusicXML decoder. Until then, model mode tries the checkpoint path and
        falls back to rule-based output when token output cannot safely become
        a GeneratedScore.
        """

        if self.backend == "hybrid_v05" or self.backend == "hybrid_v05_no_postprocess":
            return self.hybrid_v05.generate(plan)
        if self.backend == "hybrid_v04":
            plan.baseline = "hybrid_v04"
            generated = self.model_generator.generate(plan)
            if generated is not None:
                generated.metadata["generator_mode"] = "hybrid_v04"
                return generated
        if self.backend == "model":
            generated = self.model_generator.generate(plan)
            if generated is not None:
                generated.metadata.setdefault("generator_mode", "model_based")
                return generated
        generated = self.rule_based.generate(plan)
        if self.backend != "rule_based":
            generated.metadata["fallback_reason"] = f"{self.backend} unavailable; used rule_based"
        return generated

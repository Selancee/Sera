"""Model-backed symbolic generation stub.

TODO: Load a fine-tuned Transformer / LoRA checkpoint in cloud GPU inference
or local CPU-friendly quantized mode, then decode tokens into MusicXML events.
"""

from __future__ import annotations

from backend.generation.rule_based_generator import GeneratedScore
from backend.models.schemas import CompositionPlan


class ModelGenerator:
    """Placeholder for neural symbolic generation."""

    def generate(self, plan: CompositionPlan) -> GeneratedScore | None:
        """Return None until a trained model backend is configured."""

        _ = plan
        return None

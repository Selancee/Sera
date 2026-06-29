"""Optional neural symbolic model adapter for the Sera frontend.

The trained checkpoint is intentionally not committed to GitHub, so this
module has two modes:

1. checkpoint mode, enabled when SERA_SYMBOLIC_MODEL_DIR or
   SERA_SYMBOLIC_MODEL_CHECKPOINT points at a local model.pt.
2. recorded-sample mode, which exposes lightweight AutoDL run evidence already
   committed under docs/training_runs.

TODO: replace token-level output with a constrained MusicXML event decoder
before allowing this model to replace the rule-based generator.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from backend.generation.rule_based_generator import GeneratedScore
from backend.models.schemas import CompositionPlan


class ModelGenerator:
    """Load optional symbolic-model artifacts and produce qualitative samples."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.training_runs_dir = self.project_root / "docs" / "training_runs"
        self.default_model_dir = self.project_root / "models" / "sera_symbolic_small"

    def generate(self, plan: CompositionPlan) -> GeneratedScore | None:
        """Return None until the neural model can emit validated MusicXML.

        This keeps Sera's main generation pipeline stable and parseable. The
        frontend calls sample_tokens(...) for qualitative model testing.
        """

        _ = plan
        return None

    def status(self) -> dict[str, Any]:
        """Return model availability and the latest training evidence."""

        run_dir = self.latest_run_dir()
        metrics = self._read_json(run_dir / "training_metrics.json") if run_dir else {}
        samples = self._read_json(run_dir / "samples.json") if run_dir else []
        checkpoint_path = self.checkpoint_path(run_dir)
        torch_available = self._torch_available()
        checkpoint_candidates = self.checkpoint_candidates(run_dir)
        warnings: list[str] = []
        if not checkpoint_path:
            warnings.append(
                f"No local model.pt found. Put the AutoDL checkpoint in {self.default_model_dir} "
                "or set SERA_SYMBOLIC_MODEL_DIR to enable live inference."
            )
        if checkpoint_path and not torch_available:
            warnings.append("PyTorch is not installed in this Python environment; live inference is disabled.")

        return {
            "available": bool(checkpoint_path and torch_available),
            "mode": "checkpoint" if checkpoint_path and torch_available else "recorded_sample",
            "run_id": run_dir.name if run_dir else "",
            "run_dir": str(run_dir) if run_dir else "",
            "checkpoint_path": str(checkpoint_path) if checkpoint_path else "",
            "expected_model_dir": str(self.default_model_dir),
            "checkpoint_candidates": [str(path) for path in checkpoint_candidates],
            "torch_available": torch_available,
            "sample_count": len(samples) if isinstance(samples, list) else 0,
            "metrics": metrics,
            "warnings": warnings,
            "todo": "Constrain decoded tokens into valid MusicXML before routing this model into /generate.",
        }

    def sample_tokens(self, prompt: str, max_tokens: int = 96) -> dict[str, Any]:
        """Return a checkpoint-generated or recorded token sample."""

        status = self.status()
        if status["available"]:
            return self._sample_from_checkpoint(prompt, max_tokens, status)
        return self._sample_from_recorded_run(prompt, max_tokens, status)

    def checkpoint_path(self, run_dir: Path | None = None) -> Path | None:
        """Resolve the configured checkpoint path without hardcoding machines."""

        for path in self.checkpoint_candidates(run_dir):
            if path.exists():
                return path
        return None

    def checkpoint_candidates(self, run_dir: Path | None = None) -> list[Path]:
        """Return checkpoint candidates in runtime priority order."""

        explicit_checkpoint = os.environ.get("SERA_SYMBOLIC_MODEL_CHECKPOINT", "").strip()
        if explicit_checkpoint:
            path = Path(explicit_checkpoint).expanduser()
            return [path]

        explicit_dir = os.environ.get("SERA_SYMBOLIC_MODEL_DIR", "").strip()
        candidates: list[Path] = []
        if explicit_dir:
            candidates.append(Path(explicit_dir).expanduser() / "model.pt")
        if run_dir:
            candidates.append(run_dir / "model.pt")
        candidates.append(self.default_model_dir / "model.pt")
        unique_candidates: list[Path] = []
        for path in candidates:
            if path not in unique_candidates:
                unique_candidates.append(path)
        return unique_candidates

    def latest_run_dir(self) -> Path | None:
        """Return the newest committed or local training run directory."""

        if not self.training_runs_dir.exists():
            return None
        runs = [path for path in self.training_runs_dir.iterdir() if path.is_dir()]
        if not runs:
            return None
        return max(runs, key=lambda path: path.stat().st_mtime)

    def _sample_from_recorded_run(self, prompt: str, max_tokens: int, status: dict[str, Any]) -> dict[str, Any]:
        """Use committed AutoDL samples when the checkpoint is not local."""

        run_dir = Path(status["run_dir"]) if status.get("run_dir") else None
        samples = self._read_json(run_dir / "samples.json") if run_dir else []
        selected = self._select_recorded_sample(prompt, samples if isinstance(samples, list) else [])
        tokens = list(selected.get("tokens", []))[:max_tokens]
        return {
            "prompt": prompt,
            "mode": "recorded_sample",
            "model_loaded": False,
            "tokens": tokens,
            "token_text": self._tokens_to_text(tokens),
            "musicxml_preview": self._tokens_to_musicxml_preview(tokens),
            "status": status,
            "warnings": status.get("warnings", []),
        }

    def _sample_from_checkpoint(self, prompt: str, max_tokens: int, status: dict[str, Any]) -> dict[str, Any]:
        """Load model.pt and generate a short token sample."""

        import torch

        from training.train_symbolic_model import TrainSettings, generate_sample, make_model

        checkpoint = self._load_checkpoint(torch, status["checkpoint_path"])
        vocab = dict(checkpoint["vocab"])
        raw_settings = dict(checkpoint.get("settings", {}))
        setting_names = TrainSettings.__dataclass_fields__.keys()
        settings = TrainSettings(**{key: raw_settings[key] for key in setting_names if key in raw_settings})
        settings.sample_max_new_tokens = max(8, min(256, int(max_tokens)))
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = make_model(len(vocab), int(vocab["<pad>"]), settings)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        tokens = generate_sample(model, vocab, settings, device, prompt)
        return {
            "prompt": prompt,
            "mode": "checkpoint",
            "model_loaded": True,
            "tokens": tokens,
            "token_text": self._tokens_to_text(tokens),
            "musicxml_preview": self._tokens_to_musicxml_preview(tokens),
            "status": status,
            "warnings": [
                "Checkpoint output is token-level research evidence and is not yet guaranteed valid MusicXML."
            ],
        }

    @staticmethod
    def _torch_available() -> bool:
        try:
            import torch  # noqa: F401
        except ImportError:
            return False
        return True

    @staticmethod
    def _load_checkpoint(torch: Any, checkpoint_path: str) -> dict[str, Any]:
        """Load checkpoints across PyTorch versions.

        PyTorch 2.6 tightened the default loader. Sera checkpoints are local
        training artifacts, but we still prefer the explicit safe path first.
        """

        try:
            return torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        except TypeError:
            return torch.load(checkpoint_path, map_location="cpu")

    @staticmethod
    def _read_json(path: Path) -> Any:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _select_recorded_sample(prompt: str, samples: list[dict[str, Any]]) -> dict[str, Any]:
        if not samples:
            return {"prompt": prompt, "tokens": []}
        prompt_words = {piece.lower() for piece in prompt.split() if piece.strip()}
        best_sample = samples[0]
        best_score = -1
        for sample in samples:
            sample_words = {piece.lower() for piece in str(sample.get("prompt", "")).split() if piece.strip()}
            score = len(prompt_words & sample_words)
            if score > best_score:
                best_score = score
                best_sample = sample
        return best_sample

    @staticmethod
    def _tokens_to_text(tokens: list[str]) -> str:
        return " ".join(str(token) for token in tokens)

    @staticmethod
    def _tokens_to_musicxml_preview(tokens: list[str]) -> str:
        """Create a rough readable preview from XML-like tokens.

        TODO: replace this with a grammar-aware detokenizer that balances tags
        and validates against MusicXML before exposing a download button.
        """

        xml_tokens = [str(token) for token in tokens if str(token) not in {"<bos>", "<prompt>", "<score>", "<eos>"}]
        lines: list[str] = []
        for token in xml_tokens:
            if token.startswith("<") and token.endswith(">"):
                lines.append(token)
            elif lines:
                lines[-1] = f"{lines[-1]}{token}"
            else:
                lines.append(token)
        return "\n".join(lines[:120])

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

from backend.generation.rule_based_generator import GeneratedScore, RuleBasedGenerator
from backend.models.schemas import CompositionPlan


class ModelGenerator:
    """Load optional symbolic-model artifacts and produce qualitative samples."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.training_runs_dir = self.project_root / "docs" / "training_runs"
        self.active_model_name = os.getenv("SERA_ACTIVE_SYMBOLIC_MODEL", "sera_symbolic_small").strip()
        self.default_model_dir = self.project_root / "models" / self.active_model_name
        self.safe_generator = RuleBasedGenerator()

    def generate(self, plan: CompositionPlan) -> GeneratedScore | None:
        """Generate a valid score conditioned by the active neural checkpoint.

        The current trained model emits MusicXML-like tokens, but not a fully
        balanced score every time. For the main app path we therefore use the
        checkpoint output as musical conditioning, then route those conditions
        through the legal MusicXML assembler. This makes the main page use the
        trained model while keeping MIDI/PDF export stable.

        TODO: once a larger model is trained with constrained decoding, replace
        this conditioning bridge with direct model-to-MusicXML generation.
        """

        status = self.status()
        if not status["available"]:
            return None

        prompt = self._prompt_from_plan(plan)
        sample = self._sample_from_checkpoint(prompt, max_tokens=128, status=status)
        conditioned_plan, conditioning = self._condition_plan_from_tokens(plan, sample.get("tokens", []))
        generated = self.safe_generator.generate(conditioned_plan)
        generated.musicxml = generated.musicxml.replace(
            "Sera rule-based generator V0.2",
            f"Sera neural-conditioned generator ({self.active_model_name})",
        )
        generated.metadata = {
            "generator_mode": "model_conditioned",
            "model_backend": "pytorch_decoder",
            "model_name": self.active_model_name,
            "model_loaded": True,
            "model_status_mode": sample.get("mode", status.get("mode")),
            "checkpoint_path": status.get("checkpoint_path", ""),
            "conditioning": conditioning,
            "raw_model_tokens": list(sample.get("tokens", []))[:128],
            "raw_model_token_text": sample.get("token_text", ""),
            "warnings": sample.get("warnings", []),
        }
        return generated

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
            "active_model": self.active_model_name,
            "known_models": self.known_models(),
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

    def known_models(self) -> list[dict[str, str]]:
        """List local model directories available for current and future runs."""

        models_dir = self.project_root / "models"
        if not models_dir.exists():
            return []
        known: list[dict[str, str]] = []
        for path in sorted(item for item in models_dir.iterdir() if item.is_dir()):
            known.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "checkpoint": str(path / "model.pt"),
                    "available": str((path / "model.pt").exists()).lower(),
                }
            )
        return known

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
        candidates.append(self.default_model_dir / "model.pt")
        if run_dir:
            candidates.append(run_dir / "model.pt")
        unique_candidates: list[Path] = []
        for path in candidates:
            if path not in unique_candidates:
                unique_candidates.append(path)
        return unique_candidates

    @staticmethod
    def _prompt_from_plan(plan: CompositionPlan) -> str:
        intent = plan.intent
        return (
            f"{intent.title}. {intent.style} {intent.mood} music for "
            f"{', '.join(intent.instruments)} in {intent.key}, {intent.time_signature}, "
            f"{intent.tempo_bpm} bpm, {intent.bars} measures, {intent.texture}, "
            f"{intent.difficulty}. Harmony: {' '.join(intent.harmony_plan)}."
        )

    def _condition_plan_from_tokens(
        self,
        plan: CompositionPlan,
        tokens: list[str],
    ) -> tuple[CompositionPlan, dict[str, Any]]:
        """Map model token evidence into a safe measure-level plan.

        This bridge is intentionally conservative: it only reads pitch steps,
        octaves, and duration numbers from the checkpoint sample and leaves
        form, meter, and harmony under the validated planning agent.
        """

        conditioned = plan
        pitches = self._extract_pitch_names(tokens)
        durations = self._extract_durations(tokens)
        degree_hints = self._pitch_names_to_degrees(pitches, conditioned.intent.key)
        if degree_hints:
            for index, measure in enumerate(conditioned.measures):
                start = (index * 2) % len(degree_hints)
                notes = [degree_hints[(start + offset) % len(degree_hints)] for offset in range(4)]
                measure.notes = notes
                measure.description = (
                    f"{measure.description} Model-conditioned motif: {' '.join(notes)}."
                ).strip()
        conditioned.baseline = f"model_conditioned:{self.active_model_name}"
        conditioned.global_plan = dict(conditioned.global_plan)
        conditioned.global_plan["model_conditioning"] = {
            "model_name": self.active_model_name,
            "pitch_hints": pitches[:32],
            "degree_hints": degree_hints[:32],
            "duration_hints": durations[:32],
        }
        return conditioned, conditioned.global_plan["model_conditioning"]

    @staticmethod
    def _extract_pitch_names(tokens: list[str]) -> list[str]:
        pitches: list[str] = []
        pending_step = ""
        pending_alter = 0
        for index, token in enumerate(tokens):
            clean = str(token).strip()
            if clean == "<step>" and index + 1 < len(tokens):
                candidate = str(tokens[index + 1]).strip().upper()
                if candidate in {"C", "D", "E", "F", "G", "A", "B"}:
                    pending_step = candidate
                    pending_alter = 0
            elif clean == "<alter>" and index + 1 < len(tokens):
                try:
                    pending_alter = int(float(str(tokens[index + 1]).strip()))
                except ValueError:
                    pending_alter = 0
            elif clean == "<octave>" and index + 1 < len(tokens) and pending_step:
                octave_token = str(tokens[index + 1]).strip()
                if octave_token.lstrip("-").isdigit():
                    accidental = "#" if pending_alter > 0 else "b" if pending_alter < 0 else ""
                    pitches.append(f"{pending_step}{accidental}{octave_token}")
                    pending_step = ""
                    pending_alter = 0
        return pitches

    @staticmethod
    def _extract_durations(tokens: list[str]) -> list[int]:
        durations: list[int] = []
        for index, token in enumerate(tokens):
            if str(token).strip() != "<duration>" or index + 1 >= len(tokens):
                continue
            value = str(tokens[index + 1]).strip()
            if value.isdigit():
                durations.append(int(value))
        return durations

    @staticmethod
    def _pitch_names_to_degrees(pitches: list[str], key: str) -> list[str]:
        if not pitches:
            return []
        chromatic = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
        major = {0: "1", 2: "2", 4: "3", 5: "4", 7: "5", 9: "6", 11: "7"}
        minor = {0: "1", 2: "2", 3: "b3", 5: "4", 7: "5", 8: "b6", 11: "7"}
        tonic = key.split()[0].replace("-flat", "b")
        tonic_pc = chromatic.get(tonic[0].upper(), 0)
        if len(tonic) > 1:
            tonic_pc += 1 if tonic[1] == "#" else -1 if tonic[1].lower() == "b" else 0
        degree_map = minor if "minor" in key.lower() else major
        degrees: list[str] = []
        for pitch in pitches:
            step = pitch[0].upper()
            accidental = 1 if "#" in pitch else -1 if "b" in pitch else 0
            pitch_pc = (chromatic.get(step, 0) + accidental - tonic_pc) % 12
            degrees.append(degree_map.get(pitch_pc, "1"))
        return degrees

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

"""Cloud-GPU-friendly symbolic model training entrypoint.

This MVP script validates configuration and documents the extension point for
PyTorch/Transformers/Accelerate/PEFT training. It intentionally avoids loading
heavy libraries unless the command is executed in a prepared training runtime.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


def load_config(path: Path) -> dict[str, Any]:
    """Load JSON or YAML training config without downloading model weights."""

    if not path.exists():
        return {}
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    """CLI entrypoint for future model training."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens", default="data/processed/musicxml_tokens.jsonl")
    parser.add_argument("--config", default="training/configs/sera_symbolic_small.yaml")
    parser.add_argument("--out", default="data/processed/checkpoints/symbolic_lora")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)
    token_path = Path(args.tokens)
    if not token_path.exists():
        raise SystemExit(f"Token file not found: {token_path}")

    if args.dry_run:
        import json

        print(json.dumps({"tokens": str(token_path), "config": config, "out": args.out}, indent=2))
        return

    try:
        import torch  # type: ignore
        import transformers  # type: ignore
        import accelerate  # type: ignore
        import peft  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "Training dependencies are missing. Install requirements-training.txt in a cloud GPU environment."
        ) from exc

    _ = (torch, transformers, accelerate, peft)
    raise SystemExit(
        "TODO: implement decoder-only Transformer/LoRA dataset collation and trainer loop "
        "for PDMX, MetaScore, POP909, or Lakh-derived symbolic corpora."
    )


if __name__ == "__main__":
    main()

"""Train a compact symbolic decoder on MusicXML token sequences.

The default model is intentionally small enough for AutoDL budget smoke runs.
TODO: add a second trainer that fine-tunes a Hugging Face causal LM with LoRA
when larger PDMX/MetaScore corpora are available on a cloud GPU.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


SPECIAL_TOKENS = ["<pad>", "<bos>", "<eos>", "<unk>", "<prompt>", "<score>"]


@dataclass
class TrainSettings:
    """Resolved training settings used for checkpoint metadata."""

    batch_size: int = 8
    epochs: int = 3
    learning_rate: float = 3e-4
    max_sequence_length: int = 512
    d_model: int = 128
    n_layers: int = 4
    n_heads: int = 4
    dropout: float = 0.1
    dim_feedforward: int = 512
    validation_split: float = 0.1
    min_frequency: int = 1
    max_examples: int = 0
    gradient_accumulation_steps: int = 1
    seed: int = 42
    sample_max_new_tokens: int = 256


def load_config(path: Path) -> dict[str, Any]:
    """Load JSON or YAML training config without downloading model weights."""

    if not path.exists():
        return {}
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_settings(config: dict[str, Any]) -> TrainSettings:
    """Merge nested YAML config into flat trainer settings."""

    model = config.get("model", {}) or {}
    data = config.get("data", {}) or {}
    optimization = config.get("optimization", {}) or {}
    settings = TrainSettings()
    settings.batch_size = int(optimization.get("batch_size", settings.batch_size))
    settings.epochs = int(optimization.get("epochs", settings.epochs))
    settings.learning_rate = float(optimization.get("learning_rate", settings.learning_rate))
    settings.gradient_accumulation_steps = int(
        optimization.get("gradient_accumulation_steps", settings.gradient_accumulation_steps)
    )
    settings.max_sequence_length = int(model.get("max_sequence_length", settings.max_sequence_length))
    settings.d_model = int(model.get("d_model", settings.d_model))
    settings.n_layers = int(model.get("n_layers", settings.n_layers))
    settings.n_heads = int(model.get("n_heads", settings.n_heads))
    settings.dropout = float(model.get("dropout", settings.dropout))
    settings.dim_feedforward = int(model.get("dim_feedforward", settings.dim_feedforward))
    settings.validation_split = float(data.get("validation_split", settings.validation_split))
    settings.min_frequency = int(data.get("min_frequency", settings.min_frequency))
    settings.max_examples = int(data.get("max_examples", settings.max_examples))
    settings.sample_max_new_tokens = int(model.get("sample_max_new_tokens", settings.sample_max_new_tokens))
    settings.seed = int(config.get("seed", settings.seed))
    return settings


def load_token_rows(path: Path, max_examples: int = 0) -> list[dict[str, Any]]:
    """Load tokenized MusicXML JSONL rows."""

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("tokens"):
                rows.append(row)
            if max_examples and len(rows) >= max_examples:
                break
    if not rows:
        raise SystemExit(f"No token rows found in {path}")
    return rows


def prompt_tokens(prompt: str) -> list[str]:
    """Tokenize prompt text into coarse conditioning tokens."""

    return [f"prompt:{piece.lower()}" for piece in prompt.replace("\n", " ").split() if piece.strip()]


def build_vocab(rows: list[dict[str, Any]], min_frequency: int) -> dict[str, int]:
    """Build a deterministic vocabulary from prompt and MusicXML tokens."""

    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(prompt_tokens(str(row.get("prompt", ""))))
        counts.update(str(token) for token in row.get("tokens", []))
    vocab = {token: index for index, token in enumerate(SPECIAL_TOKENS)}
    for token, count in sorted(counts.items()):
        if count >= min_frequency and token not in vocab:
            vocab[token] = len(vocab)
    return vocab


def encode_rows(rows: list[dict[str, Any]], vocab: dict[str, int], settings: TrainSettings) -> list[list[int]]:
    """Encode rows as prompt-conditioned autoregressive sequences."""

    unk = vocab["<unk>"]
    encoded: list[list[int]] = []
    for row in rows:
        sequence = (
            ["<bos>", "<prompt>"]
            + prompt_tokens(str(row.get("prompt", "")))
            + ["<score>"]
            + [str(token) for token in row.get("tokens", [])]
            + ["<eos>"]
        )
        ids = [vocab.get(token, unk) for token in sequence]
        if len(ids) < 3:
            continue
        # Long MusicXML files are chunked so training remains cheap on small GPUs.
        step = max(2, settings.max_sequence_length)
        for start in range(0, len(ids) - 1, step):
            chunk = ids[start : start + settings.max_sequence_length + 1]
            if len(chunk) >= 3:
                encoded.append(chunk)
    return encoded


class SequenceDataset:
    """Tiny list-backed dataset to avoid a hard dependency on Hugging Face datasets."""

    def __init__(self, sequences: list[list[int]], pad_id: int) -> None:
        self.sequences = sequences
        self.pad_id = pad_id

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, index: int) -> list[int]:
        return self.sequences[index]

    def collate(self, batch: list[list[int]]) -> tuple[Any, Any]:
        import torch

        max_len = max(len(item) for item in batch)
        inputs = torch.full((len(batch), max_len - 1), self.pad_id, dtype=torch.long)
        labels = torch.full((len(batch), max_len - 1), self.pad_id, dtype=torch.long)
        for row_index, item in enumerate(batch):
            source = torch.tensor(item[:-1], dtype=torch.long)
            target = torch.tensor(item[1:], dtype=torch.long)
            inputs[row_index, : source.numel()] = source
            labels[row_index, : target.numel()] = target
        return inputs, labels


def split_sequences(sequences: list[list[int]], validation_split: float, seed: int) -> tuple[list[list[int]], list[list[int]]]:
    """Shuffle and split examples into train and validation chunks."""

    shuffled = list(sequences)
    random.Random(seed).shuffle(shuffled)
    val_count = max(1, int(len(shuffled) * validation_split)) if len(shuffled) > 1 else 0
    return shuffled[val_count:], shuffled[:val_count]


def make_model(vocab_size: int, pad_id: int, settings: TrainSettings) -> Any:
    """Create a compact causal Transformer."""

    import torch
    from torch import nn

    class DecoderOnlyTransformer(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.pad_id = pad_id
            self.token_embedding = nn.Embedding(vocab_size, settings.d_model, padding_idx=pad_id)
            self.position_embedding = nn.Embedding(settings.max_sequence_length, settings.d_model)
            layer = nn.TransformerEncoderLayer(
                d_model=settings.d_model,
                nhead=settings.n_heads,
                dim_feedforward=settings.dim_feedforward,
                dropout=settings.dropout,
                activation="gelu",
                batch_first=True,
            )
            self.blocks = nn.TransformerEncoder(layer, num_layers=settings.n_layers)
            self.norm = nn.LayerNorm(settings.d_model)
            self.head = nn.Linear(settings.d_model, vocab_size)

        def forward(self, input_ids: Any) -> Any:
            batch_size, seq_len = input_ids.shape
            if seq_len > settings.max_sequence_length:
                raise ValueError(f"Sequence length {seq_len} exceeds {settings.max_sequence_length}")
            positions = torch.arange(seq_len, device=input_ids.device).unsqueeze(0).expand(batch_size, seq_len)
            hidden = self.token_embedding(input_ids) + self.position_embedding(positions)
            causal_mask = torch.triu(torch.ones(seq_len, seq_len, device=input_ids.device), diagonal=1).bool()
            padding_mask = input_ids.eq(self.pad_id)
            hidden = self.blocks(hidden, mask=causal_mask, src_key_padding_mask=padding_mask)
            return self.head(self.norm(hidden))

    return DecoderOnlyTransformer()


def run_epoch(model: Any, loader: Any, optimizer: Any, device: str, pad_id: int, accumulation_steps: int) -> float:
    """Run one training epoch and return mean loss."""

    import torch
    from torch.nn import functional as F

    model.train()
    optimizer.zero_grad(set_to_none=True)
    losses: list[float] = []
    for step, (inputs, labels) in enumerate(loader, start=1):
        inputs = inputs.to(device)
        labels = labels.to(device)
        logits = model(inputs)
        loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), labels.reshape(-1), ignore_index=pad_id)
        (loss / accumulation_steps).backward()
        if step % accumulation_steps == 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
        losses.append(float(loss.detach().cpu()))
    if len(loader) % accumulation_steps:
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
    return sum(losses) / max(1, len(losses))


def evaluate_loss(model: Any, loader: Any, device: str, pad_id: int) -> float:
    """Return validation loss."""

    import torch
    from torch.nn import functional as F

    if not loader:
        return math.nan
    model.eval()
    losses: list[float] = []
    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            logits = model(inputs)
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), labels.reshape(-1), ignore_index=pad_id)
            losses.append(float(loss.detach().cpu()))
    return sum(losses) / max(1, len(losses))


def generate_sample(model: Any, vocab: dict[str, int], settings: TrainSettings, device: str, prompt: str) -> list[str]:
    """Generate a short token sample for qualitative training evidence."""

    import torch
    from torch.nn import functional as F

    id_to_token = {index: token for token, index in vocab.items()}
    eos_id = vocab["<eos>"]
    ids = [vocab["<bos>"], vocab["<prompt>"]]
    ids.extend(vocab.get(token, vocab["<unk>"]) for token in prompt_tokens(prompt))
    ids.append(vocab["<score>"])
    model.eval()
    with torch.no_grad():
        for _ in range(settings.sample_max_new_tokens):
            context = torch.tensor([ids[-settings.max_sequence_length :]], dtype=torch.long, device=device)
            logits = model(context)[0, -1] / 0.9
            top_values, top_indices = torch.topk(logits, k=min(20, logits.numel()))
            probs = F.softmax(top_values, dim=-1)
            next_id = int(top_indices[torch.multinomial(probs, num_samples=1)].item())
            ids.append(next_id)
            if next_id == eos_id:
                break
    return [id_to_token.get(index, "<unk>") for index in ids]


def train(args: argparse.Namespace) -> dict[str, Any]:
    """Train and persist checkpoint artifacts."""

    try:
        import torch
        from torch.utils.data import DataLoader
    except ImportError as exc:
        raise SystemExit("PyTorch is required for training. Install requirements-training.txt on AutoDL.") from exc

    config = load_config(Path(args.config))
    settings = resolve_settings(config)
    rows = load_token_rows(Path(args.tokens), max_examples=args.max_examples or settings.max_examples)
    vocab = build_vocab(rows, settings.min_frequency)
    sequences = encode_rows(rows, vocab, settings)
    if not sequences:
        raise SystemExit("No trainable token sequences were produced.")

    random.seed(settings.seed)
    torch.manual_seed(settings.seed)
    train_sequences, val_sequences = split_sequences(sequences, settings.validation_split, settings.seed)
    pad_id = vocab["<pad>"]
    train_dataset = SequenceDataset(train_sequences, pad_id)
    val_dataset = SequenceDataset(val_sequences, pad_id)
    train_loader = DataLoader(train_dataset, batch_size=settings.batch_size, shuffle=True, collate_fn=train_dataset.collate)
    val_loader = (
        DataLoader(val_dataset, batch_size=settings.batch_size, shuffle=False, collate_fn=val_dataset.collate)
        if val_sequences
        else None
    )

    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    model = make_model(len(vocab), pad_id, settings).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=settings.learning_rate)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    history: list[dict[str, float]] = []
    best_val = math.inf
    best_path = out_dir / "model.pt"
    for epoch in range(1, settings.epochs + 1):
        train_loss = run_epoch(
            model,
            train_loader,
            optimizer,
            device,
            pad_id,
            max(1, settings.gradient_accumulation_steps),
        )
        val_loss = evaluate_loss(model, val_loader, device, pad_id) if val_loader else math.nan
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})
        metric_for_best = val_loss if not math.isnan(val_loss) else train_loss
        if metric_for_best <= best_val:
            best_val = metric_for_best
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "vocab": vocab,
                    "settings": asdict(settings),
                    "config": config,
                    "history": history,
                },
                best_path,
            )
        print(json.dumps(history[-1], ensure_ascii=False), flush=True)

    samples = [
        {
            "prompt": row.get("prompt") or "romantic piano nocturne in A minor",
            "tokens": generate_sample(model, vocab, settings, device, row.get("prompt") or "romantic piano nocturne"),
        }
        for row in rows[: min(3, len(rows))]
    ]
    metrics = {
        "token_rows": len(rows),
        "sequence_chunks": len(sequences),
        "train_chunks": len(train_sequences),
        "validation_chunks": len(val_sequences),
        "vocab_size": len(vocab),
        "device": device,
        "settings": asdict(settings),
        "history": history,
        "best_loss": best_val,
        "seconds": round(time.time() - started, 3),
        "checkpoint": str(best_path),
    }
    (out_dir / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "training_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "samples.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    """CLI entrypoint for local smoke tests and AutoDL training."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens", default="data/processed/musicxml_tokens.jsonl")
    parser.add_argument("--config", default="training/configs/sera_symbolic_small.yaml")
    parser.add_argument("--out", default="data/processed/checkpoints/sera_symbolic_small")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-examples", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    token_path = Path(args.tokens)
    if not token_path.exists():
        raise SystemExit(f"Token file not found: {token_path}")
    config = load_config(Path(args.config))
    settings = resolve_settings(config)
    if args.max_examples:
        settings.max_examples = args.max_examples
    if args.dry_run:
        rows = load_token_rows(token_path, max_examples=settings.max_examples)
        vocab = build_vocab(rows, settings.min_frequency)
        sequences = encode_rows(rows, vocab, settings)
        print(
            json.dumps(
                {
                    "tokens": str(token_path),
                    "config": config,
                    "settings": asdict(settings),
                    "rows": len(rows),
                    "sequence_chunks": len(sequences),
                    "vocab_size": len(vocab),
                    "out": args.out,
                },
                indent=2,
            )
        )
        return
    metrics = train(args)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

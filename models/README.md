# Sera Symbolic Model Artifacts

Runtime checkpoints are intentionally ignored by Git. Put trained model folders here:

```text
models/
  sera_symbolic_small/
    model.pt
    vocab.json
    training_metrics.json
  sera_symbolic_large/
    model.pt
    vocab.json
```

Default runtime:

```powershell
$env:SERA_ACTIVE_SYMBOLIC_MODEL = "sera_symbolic_small"
$env:SERA_SYMBOLIC_MODEL_DIR = "D:\Sera\models\sera_symbolic_small"
$env:SERA_GENERATOR_BACKEND = "model"
```

Future larger checkpoints can be enabled without code changes:

```powershell
$env:SERA_ACTIVE_SYMBOLIC_MODEL = "sera_symbolic_large"
$env:SERA_SYMBOLIC_MODEL_DIR = "D:\Sera\models\sera_symbolic_large"
D:\Sera\stop_app.bat
D:\Sera\run_app.bat
```

The current production score path is model-conditioned: the checkpoint supplies token-level musical hints, and Sera's safe
MusicXML assembler produces valid score, MIDI, and PDF artifacts. TODO: route future large models through a constrained
MusicXML decoder when their output can be validated directly.

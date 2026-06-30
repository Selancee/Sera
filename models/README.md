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
  sera_v05_50rmb/
    model.pt
    vocab.json
    training_metrics.json
    training_config_snapshot.json
    samples.json
    sha256_manifest.txt
    model_card.json
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

Runtime selection is exposed in the Model tab and through the API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/model/registry
Invoke-RestMethod http://127.0.0.1:8000/model/select `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"model_name":"sera_symbolic_large","persist":true}'
```

The UI and API persist the selected model to `.env` by default, replacing only Sera's model-related keys. Use
`"persist":false` for a process-local switch.

## 50 RMB Verification Model

The budget-capped AutoDL run writes two remote copies:

```text
/root/autodl-tmp/sera_runs/<run_id>
/root/autodl-tmp/sera_models/<run_id>
```

Fetch the persistent copy into Sera:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\fetch_autodl_model.ps1 `
  -SshTarget root@<autodl-host> `
  -Port <ssh-port> `
  -RemoteRunDir /root/autodl-tmp/sera_models/<run_id> `
  -ModelName sera_v05_50rmb

powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\verify_model_artifacts.ps1 `
  -ModelDir D:\Sera\models\sera_v05_50rmb
```

Keep `sha256_manifest.txt` and `model_card.json` with the checkpoint. They are the recovery record for the technical verification run.

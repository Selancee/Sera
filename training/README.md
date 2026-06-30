# Sera V0.5 Training

V0.5 no longer trains only "full MusicXML from zero." The small model is trained on local symbolic tasks so it learns rhythm, contour, motif, and cadence choices without owning final MusicXML legality.

## Build Data

```powershell
python -m training.augmentation.build_augmented_dataset --input_dir examples/scores --output_dir data/augmented
python -m training.tasks.build_multitask_dataset --input_dirs data/fragments data/augmented examples/scores --output data/tokenized_v05/multitask_dataset.jsonl
```

## Tokenize

```powershell
python -m training.tokenization.structured_tokenizer --input data/tokenized_v05/multitask_dataset.jsonl
```

## Smoke Test

```powershell
python training/train_symbolic_model.py --config training/configs/sera_v05_smoke.yaml --dry-run
```

## 50 RMB AutoDL Technical Verification

This run is for budget-capped proof, not final quality. It caps training time, limits dataset size, and saves every usable model artifact under both the run folder and the persistent AutoDL data disk.

```powershell
powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\run_autodl_50rmb_training.ps1 `
  -SshTarget root@<autodl-host> `
  -Port <ssh-port> `
  -MaxExamples 1200 `
  -MaxFiles 1200 `
  -Epochs 6 `
  -MaxRunHours 20
```

Remote outputs:

```text
/root/autodl-tmp/sera_runs/<run_id>/
  model.pt
  vocab.json
  training_metrics.json
  training_config_snapshot.json
  samples.json
  train.log

/root/autodl-tmp/sera_models/<run_id>/
  model.pt
  vocab.json
  sha256_manifest.txt
  model_card.json

/root/autodl-tmp/sera_models/<run_id>.tar.gz
```

Copy the model back and verify hashes:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\fetch_autodl_model.ps1 `
  -SshTarget root@<autodl-host> `
  -Port <ssh-port> `
  -RemoteRunDir /root/autodl-tmp/sera_models/<run_id> `
  -ModelName sera_v05_50rmb

powershell -ExecutionPolicy Bypass -File D:\Sera\scripts\verify_model_artifacts.ps1 `
  -ModelDir D:\Sera\models\sera_v05_50rmb
```

## Small Model

```powershell
python training/train_symbolic_model.py --config training/configs/sera_v05_small.yaml --out models/sera_v05_small
```

The trainer writes `training_metrics.json`, `training_config_snapshot.json`, `samples.json`, `vocab.json`, and the best `model.pt`. Metrics include `task_counts` and `task_loss_history`.

## Current Limits

The V0.5 trainer is still a compact native PyTorch decoder. It supports the new data format and logs per-task proxy loss, but real quality depends on a larger and cleaner MusicXML/fragment corpus.

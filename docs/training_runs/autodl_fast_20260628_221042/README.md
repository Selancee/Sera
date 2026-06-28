# Sera AutoDL Training Run

- run_id: autodl_fast_20260628_221042
- machine: AutoDL vGPU-48GB hourly instance
- dataset: Sera generated examples + ASAP GitHub MusicXML files
- max_examples: 120
- epochs: 2
- max_sequence_length: 128
- model: native PyTorch decoder-only Transformer, d_model=64, layers=2
- output_dir: /root/autodl-tmp/sera_runs/autodl_fast_20260628_221042

Artifacts:
- model.pt
- vocab.json
- training_metrics.json
- samples.json
- baseline_score_eval.json
- train.log

Note: model.pt (121 MB) and vocab.json (14 MB) were kept on the AutoDL instance
and not committed to GitHub. This folder stores the lightweight run evidence.

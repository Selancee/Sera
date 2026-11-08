# softwarex_deepseek_core_20261002_v1

Result class: formal_live
Scored live-provider experiment.

Existing development benchmark; single model, one stochastic draw, no held-out generalization claim.

| Condition | Strict editing success | Outputs | Outputs with leakage | Correct refusal | Estimated USD |
|---|---:|---:|---:|---:|---:|
| full_rewrite | 72/110 | 105 | 17 | 10/10 | 0.6537 |
| patch_only | 65/110 | 92 | 18 | 10/10 | 0.1568 |
| sera_full | 63/110 | 73 | 0 | 10/10 | 0.2213 |

Strict success: Task constraints AND valid MusicXML AND complete non-target preservation AND output produced without refusal.

Leakage is measured among produced editing outputs; rejection is not a successful edit.

Repairs are additional calls available only to Sera Full. This is a system comparison, not a matched-call-budget causal estimate.

Configured peak cache-miss rates; conservative estimate, not a billing receipt.

Paired source-cluster bootstrap intervals are exploratory; the 120 tasks are not 120 independent scores.

```json
{
  "patch_only-minus-full_rewrite": {
    "task_count": 110,
    "source_clusters": 20,
    "difference": -0.06363636363636363,
    "percentile_95_ci": [
      -0.18584070796460178,
      0.06363636363636363
    ],
    "replicates": 5000,
    "seed": 42
  },
  "sera_full-minus-full_rewrite": {
    "task_count": 110,
    "source_clusters": 20,
    "difference": -0.08181818181818182,
    "percentile_95_ci": [
      -0.21100917431192662,
      0.05504587155963303
    ],
    "replicates": 5000,
    "seed": 42
  },
  "sera_full-minus-patch_only": {
    "task_count": 110,
    "source_clusters": 20,
    "difference": -0.01818181818181818,
    "percentile_95_ci": [
      -0.0625,
      0.026785714285714284
    ],
    "replicates": 5000,
    "seed": 42
  }
}
```

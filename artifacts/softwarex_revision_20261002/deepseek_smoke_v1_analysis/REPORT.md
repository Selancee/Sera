# softwarex_deepseek_smoke_20261002_v1

Result class: live_non_formal
These results are not formal model evidence.

Existing development benchmark; single model, one stochastic draw, no held-out generalization claim.

| Condition | Strict editing success | Outputs | Outputs with leakage | Correct refusal | Estimated USD |
|---|---:|---:|---:|---:|---:|
| full_rewrite | 3/5 | 5 | 1 | 1/1 | 0.0201 |
| patch_only | 2/5 | 3 | 0 | 1/1 | 0.0071 |
| sera_full | 0/5 | 0 | 0 | 1/1 | 0.0082 |

Strict success: Task constraints AND valid MusicXML AND complete non-target preservation AND output produced without refusal.

Leakage is measured among produced editing outputs; rejection is not a successful edit.

Repairs are additional calls available only to Sera Full. This is a system comparison, not a matched-call-budget causal estimate.

Configured peak cache-miss rates; conservative estimate, not a billing receipt.

Paired source-cluster bootstrap intervals are exploratory; the 120 tasks are not 120 independent scores.

```json
{
  "patch_only-minus-full_rewrite": {
    "task_count": 5,
    "source_clusters": 2,
    "difference": -0.2,
    "percentile_95_ci": [
      -1,
      0
    ],
    "replicates": 5000,
    "seed": 42
  },
  "sera_full-minus-full_rewrite": {
    "task_count": 5,
    "source_clusters": 2,
    "difference": -0.6,
    "percentile_95_ci": [
      -1,
      -0.5
    ],
    "replicates": 5000,
    "seed": 42
  },
  "sera_full-minus-patch_only": {
    "task_count": 5,
    "source_clusters": 2,
    "difference": -0.4,
    "percentile_95_ci": [
      -0.5,
      0
    ],
    "replicates": 5000,
    "seed": 42
  }
}
```

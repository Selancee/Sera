# DeepSeek three-condition demonstration — 2 October 2026

The real-provider comparison completed all 360 task-condition runs. Independent
recomputation matched every metric row and all 14 integrity checks passed. There
were no provider failures, budget stops or truncated responses. The producer was
clean commit `e3a34e1`; all 403 main-experiment responses identify `deepseek-flash`
and finish with `stop` (360 initial generations plus 43 repair calls).

## Results and interpretation

| Condition | Strict editing success / 110 | Produced editing scores | Scores with non-target changes | Correct refusal / 10 | Erroneous refusal on editing tasks | Estimated USD |
|---|---:|---:|---:|---:|---:|---:|
| Full Rewrite | 72 (65.5%) | 105 | 17/105 | 10/10 | 5 | 0.6537 |
| Patch Only | 65 (59.1%) | 92 | 18/92 | 10/10 | 10 | 0.1568 |
| Sera Full | 63 (57.3%) | 73 | 0/73 | 10/10 | 34 | 0.2213 |

Strict editing success requires satisfaction of the frozen benchmark constraints,
valid MusicXML, complete non-target preservation and an actual output without
refusal. Constraint-only editing success is 88/110, 65/110 and 63/110, respectively.
The 10 expected-refusal tasks are separate from the 110 executable tasks. Rejected
or erroneously refused edits are not successes, and low output coverage cannot be
used to claim high editing accuracy.

This run demonstrates an observable protection/coverage tradeoff. Sera Full's
accepted outputs had no measured non-target changes, but it produced fewer outputs
and had lower observed strict success than Full Rewrite. Patch Only also did not
outperform rewriting overall. These results **do not support a claim of generally
higher editing success from structured patches**. They support the software's
ability to measure and constrain unwanted changes while revealing rejection costs.

Paired source-cluster bootstrap estimates (5,000 resamples, 20 source scores):

| Strict-success difference | Percentage points | Exploratory 95% interval |
|---|---:|---:|
| Patch Only minus Full Rewrite | -6.36 | [-18.58, 6.36] |
| Sera Full minus Full Rewrite | -8.18 | [-21.10, 5.50] |
| Sera Full minus Patch Only | -1.82 | [-6.25, 2.68] |

These are exploratory intervals for this small development set, not evidence of
superiority or population-wide equivalence. All failures and categories are retained
in the machine-readable analysis; the run was not repeated to select better results.

## Repair and efficiency

Replaying the same saved initial Sera Full responses with model repair disabled
required zero network calls. Correct outcomes (strict edit or correct refusal)
increased from 62/120 to 73/120 after repair: 11 improvements across 39 tasks receiving
43 returned repair calls. Twenty-five repaired editing tasks ended in erroneous
refusal. The legacy `repair_success` metric counts a valid transaction or refusal;
it must not be described as 36 successful edits. The stricter replay analysis makes
this distinction explicit.

Median end-to-end recorded latency was 9.93 s for Full Rewrite, 2.05 s for Patch Only
and 2.27 s for Sera Full. Total input/output tokens were 543,686/408,823,
413,461/27,262 and 595,858/35,416, respectively. Costs use the configured peak,
cache-miss rates and are estimates rather than invoices. Main experiment: USD
1.0317027. Both retained pilots: USD 0.0727236. Total: **USD 1.1044263**.

## Protocol and limitations

The frozen `answer_blind_v3` protocol supplies the same instruction/scopes to all
conditions and identical initial messages/schema to both patch conditions. It
excludes Gold patches, expected-status labels, scoring constraints and unsupported
reasons. Initial outputs are separate model generations, not identical samples;
temperature zero is not a reproducibility guarantee. Only Sera Full receives model
repair, so this is a system comparison rather than a matched-call-budget estimate.

Two six-task live pilots preceded core; the first exposed ambiguous public JSON
contract documentation. The clarification and all negative pilot outputs are retained
and disclosed in `LIVE_EXPERIMENT_PROTOCOL.md`. Pilot tasks overlap core. All 120
tasks are from the existing development benchmark; no held-out/generalization or
musical-preference claim follows. The API returns an alias, not an immutable model
snapshot; the request date, reported model, configuration and outputs are saved.

Scoring also has operational assumptions. For example, `insertion_001` requires
deletion/insertion according to its frozen constraints even though a model can
interpret “replace the final note” as an in-place pitch change. The scores above
use the unchanged, pre-existing scorer; alternative musical-equivalence criteria
would require a separately defined sensitivity analysis. No metric was changed
after observing the main results.

The separate validator study detected 180/180 constructed invalid patches after
the documented `dynamic_equals` fix, while rejecting 3/20 canonical-valid edits
because of grace-note dynamic round-trip limitations. These measurements are
bounded fault-injection/regression evidence, not proof of arbitrary semantic safety.

## Evidence and reproduction

- Main experiment: `experiments/softwarex_deepseek_core_20261002_v1/`.
- Both pilots: `experiments/softwarex_deepseek_smoke_20261002_v1/` and `_v2/`.
- Main `audit/` contains the independent 14-check report and recomputed metrics.
- Main `analysis/` contains condition/category tables, cluster intervals, and
  initial-versus-repaired case records.
- `DEEPSEEK_LIVE_VALIDATION.json` records the run totals and publication status.
- `VALIDATOR_DETECTION_REPORT.md` links full pre/post mutation evidence.

```powershell
.\.venv\Scripts\python.exe scripts/verify_reproducibility.py --experiment softwarex_deepseek_core_20261002_v1 --skip-tests --output-dir artifacts/new_deepseek_audit
.\.venv\Scripts\python.exe scripts/analyze_softwarex_live.py --experiment softwarex_deepseek_core_20261002_v1 --output artifacts/new_deepseek_analysis
.\.venv\Scripts\python.exe scripts/analyze_softwarex_repairs.py --experiment softwarex_deepseek_core_20261002_v1 --output artifacts/new_deepseek_analysis
```

These commands use saved outputs and require no API key. The release tag, original
deposit and submission baseline are unchanged. New data and revised manuscript
remain local; release metadata, final rendering and remaining P1 review points
must be completed before submission.

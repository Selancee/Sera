# DeepSeek revision experiment protocol

Date: 2026-10-02. The author selected DeepSeek and authorized the tests.
No credential belongs in this document, a configuration, Git or an experiment artifact.

## Frozen comparison

- One provider/model: official DeepSeek endpoint, `deepseek-flash`.
- Official documentation currently identifies this alias as DeepSeek-V4.1-Flash.
  Record the response model string and run timestamp; an alias is not an immutable
  model snapshot. Source: https://api-docs.deepseek.com/updates/.
- 120 existing core tasks, one repetition, three conditions (360 initial requests).
  A separate six-task smoke run overlaps core and is not pooled into its results.
- Temperature 0, non-thinking mode explicitly selected, no API seed (unsupported),
  output cap 8192, concurrency 3, 180-second timeout, no transport retry or cache.
- At most two model repair requests for Sera Full, with every returned response
  and repair prompt retained. Full Rewrite and Patch Only receive no repairs.
- Smoke budget USD 1, core budget USD 9; persistent reservation ledger survives
  interruption. Cost estimates use peak/cache-miss prices (USD 0.30 input and
  USD 1.20 output per million tokens), conservatively ignoring discounts.
  These are estimates, not actual billing receipts. Price source checked 2026-10-02:
  https://api-docs.deepseek.com/quick_start/pricing/?tab=case-studies.

## Information and scoring boundaries

The answer-blind protocols allowlist the English instruction, target scope,
protected scope and source score. No expected status, unsupported reason, Gold
patch, expected output, scoring constraint or task ID enters a live request.
Patch Only and Sera Full receive identical initial messages, schema and compact
context. Full Rewrite receives the same user instruction/scopes plus full XML.
All conditions may explicitly refuse. Only Sera Full applies transaction checks,
enforces the original user scopes against model-declared scope changes, and repairs.
The scope guard uses user inputs, never scoring answers.

The model receives public operation argument documentation, not solved examples.
Legacy prompt versions remain available for reproducing frozen fixture evidence;
new formal live runs require an answer-blind protocol. The core comparison uses
`answer_blind_v3`, following the retained pilot described below. A sentinel test checks all 120 task inputs and
the repair builder for answer leakage. Implementation hashes prevent resuming a
v2 experiment after producer code changes.

### Retained pilot intervention

The first live pilot (`softwarex_deepseek_smoke_20261002_v1`, v2 prompts) completed
18 initial requests and one repair, with a peak-rate estimate of USD 0.0353778.
Its 14 integrity/recomputation checks passed before any code change. Inspection
showed that the public prompt documentation did not specify the type-tagged JSON
forms of preconditions/effects, and did not explain that operation change counts
refer to event IDs rather than global attributes. Unsupported assertion formats
caused rejection even when the proposed edit itself was plausible.

The v3 protocol clarifies these public API forms identically for both patch arms.
It does not supply task answers, change any validator or relax any scoring rule.
The v2 prompts and negative pilot results are retained. A second pilot has a new
ID (`softwarex_deepseek_smoke_20261002_v2`) and a USD 0.95 cap; together with the
first pilot's actual estimate and the USD 9 core cap, the remaining plan stays
below USD 10. These pilot tasks overlap core: the resulting demonstration is
development-benchmark evidence, not held-out evaluation. No main core result was
inspected before this protocol clarification.

Report executable-task success separately from correct refusal. The strict editing
criterion requires task constraints, XML validity, complete non-target preservation,
and an actual output without refusal. Also report constraint-only success, output
coverage, leakage among produced outputs, erroneous refusal, repair calls, token
usage, latency, and all failures. Rejected edits do not count as successful edits.
Use paired comparisons with bootstrap resampling by source score (20 clusters),
not an assumption that all 120 instructions are independent. Confidence intervals
are exploratory. System-level differences do not isolate patch representation
from repair's additional call budget.

This is a software demonstration on the existing development benchmark, not
held-out generalization. Do not tune prompts against core results and then silently
replace the experiment. Any intervention requires a new ID and disclosure.

## Validator study

`scripts/run_validator_detection_study.py` uses all 20 synthetic source scores.
It constructs one canonical valid dynamic edit and nine independently specified
mutations per source: missing schema, stale fingerprint, absent event, protected
edit, duration overflow, orphan tie/slur, pitch preservation violation, and wrong
dynamic semantics. Labels are defined by construction, not by validator outputs.
No Gold patch or LLM is used. Save complete patches, transaction results, source
hashes, exceptions, unchanged-caller checks and rollback fingerprints.

Initial pilot v1 exposed an overbroad valid-control assumption for chord members.
The v2 constructor excludes chords/simultaneous onsets; all pilot results remain
under `artifacts/softwarex_revision_20261002/`. Three remaining control rejections
involve grace-note dynamics during XML round-trip. Distinguish canonical edit
validity from export representability: these are end-to-end rejections, not proof
that the notation fidelity checker misidentified an actual round-trip mismatch.

The pre-fix v2 study exposed a silently ignored `dynamic_equals` postcondition.
Its checker now verifies an explicit event ID/value, reports a mismatch or missing
event as E15 and an unsupported declaration shape as E19. Retain pre/post results;
testing this fix on the same mutations is regression evidence. Other silently
accepted effect names and arbitrary instruction semantics are not certified by
this narrow study and must not be described as fully validated.

## Commands

Set `DEEPSEEK_API_KEY` in the local environment; never paste it into these commands.

```powershell
$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY','User')
.\.venv\Scripts\python.exe scripts/run_smoke_experiment.py --config evaluation/configs/softwarex_deepseek_smoke_v2.yaml
.\.venv\Scripts\python.exe scripts/run_core_experiment.py --config evaluation/configs/softwarex_deepseek_core.yaml
.\.venv\Scripts\python.exe scripts/verify_reproducibility.py --experiment softwarex_deepseek_core_20261002_v1 --skip-tests --output-dir artifacts/softwarex_revision_20261002/deepseek_core_audit
.\.venv\Scripts\python.exe scripts/analyze_softwarex_live.py --experiment softwarex_deepseek_core_20261002_v1 --output artifacts/softwarex_revision_20261002/deepseek_core_analysis
```

Run smoke and inspect transport/protocol integrity before core. Do not infer
experimental completion or model performance from the existence of these commands.

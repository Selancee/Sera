# SoftwareX reproducibility protocol

## Claim classes

SeraEdit separates three evidence classes:

1. **Automated software verification**: tests, schema checks, round trips, package
   health and deterministic fixtures. These results are reportable as engineering
   verification.
2. **Model evaluation**: runs from a named remote/local model using frozen prompts,
   task split and provider metadata. No complete formal run is included here.
3. **Benchmark task review**: human inspection of instructions, scopes, Gold outputs,
   deterministic diffs, and host-visible notation. This is complete for the core split.
4. **Musical-quality evaluation**: blinded multi-reviewer musician/performer review.
   This remains future work and is not substituted by task-correctness review or local
   theoretical proxies.

## Verification dataset

The core split contains 120 tasks over 20 short synthetic CC0 MusicXML scores. Each
task declares target/protected scope, expected constraints and either a gold patch or
an expected refusal. Automatic validation checks existence, schema, gold application,
constraint evaluation and MusicXML round trip. The frozen human-review snapshot records
120/120 primary decisions and a stratified 30/30 repeat check with zero stale records.
Both passes use the same pseudonymous reviewer, so no inter-rater claim is made.

## Reproduction

Follow `INSTALLATION.md`, then run:

```powershell
.\.venv\Scripts\python.exe scripts\run_reviewer_demo.py
.\.venv\Scripts\python.exe scripts\validate_benchmark.py --split core --write-report
.\.venv\Scripts\python.exe scripts\run_core_experiment.py --config evaluation\configs\core_mock.yaml --experiment-id softwarex_verification_120_v1
.\.venv\Scripts\python.exe scripts\run_runtime_acceptance.py --split core --mode local --language en --language zh --repetitions 3 --host-scope-mode exact --experiment-id runtime_acceptance_core_bilingual_r3_v4_20260826 --fail-on-task-failure
.\.venv\Scripts\python.exe scripts\export_runtime_acceptance_evidence.py --source experiments\runtime_acceptance_core_bilingual_r3_v4_20260826 --output experiments\softwarex_runtime_acceptance_720_v4
.\.venv\Scripts\python.exe scripts\run_runtime_acceptance.py --split core --mode local --language en --language zh --host-scope-mode expanded_adjacent --experiment-id runtime_acceptance_host_roundtrip_scope_v2_20260826 --fail-on-task-failure
.\.venv\Scripts\python.exe scripts\export_runtime_acceptance_evidence.py --source experiments\runtime_acceptance_host_roundtrip_scope_v2_20260826 --output experiments\softwarex_host_scope_robustness_240_v3
.\.venv\Scripts\python.exe scripts\export_human_review_evidence.py --json <REVIEW_EXPORT.json> --csv <REVIEW_EXPORT.csv> --output experiments\softwarex_human_review_120_v1
.\.venv\Scripts\python.exe scripts\verify_reproducibility.py --experiment softwarex_verification_120_v1 --skip-tests
```

The runner saves a manifest, config/prompt/benchmark hashes, JSONL runs, raw and
normalized outputs, metrics and errors without overwriting a completed experiment.
The verifier recomputes metrics and detects evidence drift.

For first-pass review, `scripts/run_reviewer_demo.py` is the recommended entry point.
It exercises pitch, dynamics, key signature, meter/deletion, voice movement and safe
refusal through the actual local product path, then verifies host MusicXML round trips.
The larger commands above reproduce the frozen publication evidence.

## Expected verified outcome for this release candidate

- benchmark: 120 valid, 0 invalid;
- human review: 120/120 primary, 30/30 stratified repeat check, 0 stale records;
- experiment cases: 360 expected and completed, 0 execution errors;
- result class: `mock_non_formal`;
- formal results allowed: `false`;
- drift checks: config, benchmark, prompt, dependency, evidence, metric rows and run
  count all true.

Latency from the deterministic fixture is machine/load dependent and is retained in
the raw summary for debugging; it is not a provider/model latency result.

The separate product-runtime acceptance replay does not feed Gold patches to the
generator. It passes each English and Chinese instruction through
`generate_patch_with_runtime`, transaction preview, commit, protected-scope checks,
deterministic task constraints, source-preserving patching of the original MusicXML, and
host-output re-import. The release snapshot
contains 720/720 passing runs (120 tasks x 2 languages x 3 repetitions), 60 correct
refusals, zero unsafe executions, 660/660 successful source-preserving host exports,
100% MusicXML validity, complete protected-scope preservation of 1.0, and identical patch/output
fingerprints in all 240 repeated task-language groups. This is offline product
acceptance evidence, not remote-model accuracy. The publication snapshot records SHA-256
hashes for all 1,380 original raw/host files and carries 220 compact host outputs so every
executable task-language pair can be opened from the frozen desktop review workspace.
All 120 task groups also produced semantically equivalent patches and identical final
score fingerprints across English and Chinese instructions.

The separate host-selection robustness replay widens every eligible instruction that
explicitly names a measure by one adjacent measure before calling the same product
entrypoint. It completed 240/240 bilingual runs. Expansion was applicable in 174 runs,
and all 174 retained the benchmark target, constraints, protected content and final
MusicXML. All 220 executable runs completed source-preserving host export/re-import.
The remaining 66 runs were not widened because the instruction did not name
one specific measure, the source had no adjacent measure, or the task was whole-score.
This guards against host-selection/semantic-target localization regressions; it is not
evidence of remote-model accuracy.

## External reproducibility boundary

A permanent archive DOI, public release tag and public repository snapshot must be
added before submission. API-based experiments additionally require the reader's own
provider key and may change with provider model versions. The mock verification path
is offline and costs no tokens.

# SoftwareX reproducibility protocol

## Claim classes

SeraEdit separates four evidence classes:

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

The original `v1.0.0` fixture is retained as historical evidence. The revision audit
reproduced its benchmark/dependency hash mismatch and six metric-row differences.
Use the separately generated `softwarex_revision_verification_120_v2` snapshot for
the corrected offline protocol. Do not resume or regenerate the original experiment
under its old identifier. See the revision's `P0_REPRODUCIBILITY_REPORT.md` for the
diagnosis and the exact environment and source revision tested.

Follow `INSTALLATION.md`, then run:

```powershell
.\.venv\Scripts\python.exe scripts\run_reviewer_demo.py
.\.venv\Scripts\python.exe scripts\validate_benchmark.py --split core --write-report
.\.venv\Scripts\python.exe scripts\verify_reproducibility.py --experiment softwarex_revision_verification_120_v2 --skip-tests --output-dir artifacts\revision_reproducibility
.\.venv\Scripts\python.exe scripts\run_core_experiment.py --config evaluation\configs\softwarex_revision_mock.yaml --experiment-id local_reviewer_fixture
.\.venv\Scripts\python.exe scripts\verify_reproducibility.py --experiment local_reviewer_fixture --skip-tests --output-dir artifacts\fresh_fixture_reproducibility
```

The runner saves a manifest, config/prompt/benchmark hashes, JSONL runs, raw and
normalized outputs, metrics and errors without overwriting a completed experiment.
The verifier recomputes metrics and detects evidence drift.

For first-pass review, `scripts/run_reviewer_demo.py` is the recommended entry point.
It exercises pitch, dynamics, key signature, meter/deletion, voice movement and safe
refusal through the actual local product path, then verifies host MusicXML round trips.
The first verifier recomputes the frozen revision metrics without generating outputs.
The second experiment generates fresh fixture outputs under a new identifier. Its
latencies will differ; each run must reproduce its own saved metrics exactly.

For POSIX shells, use `python` from the activated environment and forward slashes in
the same commands. The current revision audit reports Windows execution only.

New manifests include per-file input and raw/normalized-output SHA-256 hashes. The
version 2 dependency digest also covers the tested dependency constraints and
publication requirements. Resume refuses benchmark, dependency or evidence drift.
`.gitattributes` preserves exact bytes of benchmark inputs, dependency files and
published evidence, including the original human-review file hashes. The verifier
reports differing metric fields and verifies the human-review evidence hashes.

To validate the distributable rather than the development checkout:

```powershell
.\.venv\Scripts\python.exe scripts\export_softwarex_package.py --artifact-label revision-candidate --output-dir artifacts\source_candidate
.\.venv\Scripts\python.exe scripts\verify_softwarex_source_archive.py artifacts\source_candidate\seraedit-revision-candidate-source.zip --output-dir artifacts\source_archive_verification
```

The archive verifier checks every manifest entry, extracts to a separate temporary
directory, clears `PYTHONPATH`, and executes the verifier, reviewer demo and test
suite there. It uses the selected interpreter's installed dependencies; this is
source-package isolation, not proof of a fresh dependency installation. CI runs the
same archive check after installing the documented dependencies.

## Expected outcome of the corrected offline fixture

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
generator. The rule generator was developed using these benchmark instructions,
including correction of the Chinese preserve-pitch/tenuto ambiguity after inspecting
cross-language results. Accordingly, 720/720 is regression evidence on a development
benchmark, not evidence of generalization to unseen instructions. The 720 executions
are 120 tasks in two languages with three deterministic repetitions, not 720
independent tasks. It passes each English and Chinese instruction through
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

The public repository, immutable release tag, and public Zenodo software deposit are
available. Version DOI `10.5281/zenodo.22128976` resolves to the archived SeraEdit
1.0.0 source release; concept DOI `10.5281/zenodo.22128975` resolves to the latest
Zenodo version. API-based experiments additionally require the reader's own provider
key and may change with provider model versions. The mock verification path is offline
and costs no tokens.

The DOI above identifies the original deposit. Local revision candidates and their
new verification snapshot are not covered by that deposit until a separate updated
release is published. A local passing audit does not establish a passing hosted CI run.

## Real-provider revision evidence

`softwarex_deepseek_core_20261002_v1` is separate from the mock and rule replays.
It contains 360 completed task-condition runs, dated 2 October 2026, reporting the
API alias deepseek-flash. All 14 checks passed in clean source ff82c74 and its isolated
ZIP; 445 Python tests and the six-task reviewer demo also passed. Strict editing
success was 72/110, 65/110 and 63/110 for Full Rewrite, Patch Only and Sera Full.
Sera Full had 0/73 output scores with measured leakage and 34 erroneous refusals.
These results do not show improved overall success or held-out generalization.

The standalone validator study has 180 rejected invalid mutations and 3/20 valid
controls rejected because of grace-dynamic round-trip limitations. Same-case fixes
are regression evidence. All pilot failures and pre-fix cases are retained. Consult
`paper/softwarex/revisions/2026-10_minor_r1/DEEPSEEK_RESULTS.md` and
`VALIDATOR_DETECTION_REPORT.md` before interpreting aggregate metrics.

# SoftwareX P0 reproducibility repair

Date: 2 October 2026. Scope: offline reproducibility; live API experiments deferred
at the author's request. The original `v1.0.0` tag, deposited source ZIP and frozen
submission files are retained. This report concerns a local revision candidate.

## Reproduced original failures

The original tag was extracted into a separate directory and tested with the local
Python 3.12 environment. `verify_reproducibility.py --experiment
softwarex_verification_120_v1 --skip-tests` exited 1. The false checks were
`benchmark_hash`, `dependency_lock_hash`, and `metric_rows_equal`.

| Evidence | Observation and cause |
| --- | --- |
| Six differing metric rows | `dynamics_001` changed from two to three constraints in each condition. `meter_001` changed from three to nine; its saved output satisfies two of the current nine, changing task success from 1 to 0 in all three conditions. Saved metrics and final task definitions were not synchronized. |
| Dependency digest | The manifest names an earlier development commit and `dirty: true`. `pyproject.toml`, `requirements.txt`, and `frontend/package-lock.json` changed between that commit and release. Neither LF nor CRLF normalization makes released files match the recorded digest; line endings alone do not explain this failure. |
| Original tag tests | 411 collected, 410 passed, 1 failed, 0 skipped in this environment. The failing export test reads the ignored `runtime_acceptance_core_bilingual_r3_v3_20260825` directory. The reviewer's 409 passed / 1 skipped differs with environment; neither supports the manuscript's 408 count for the tag. |
| Deposited source ZIP | The retained ZIP matches the recorded published SHA-256 `7ae6a9ab20c29279fb04872fee8fa549d4f6a361dba571821c38c608c4b4e0e6`. Its verifier cannot import `evaluation.analysis`. Archive selection omitted required evaluation modules. |
| Human-review evidence | All four current frozen files match their recorded byte counts and SHA-256. They must remain byte-preserved across checkout and ZIP export. |

A later passing run does not retroactively make the original tag or deposit reproducible.

## Repairs

- The ignored-directory test had already been repaired after the original tag. It
  now builds a small fixture and separately checks the tracked 720-run snapshot.
- Source export includes required evaluation modules, training modules used by
  regression tests, backend/desktop packaging entry points, launchers, branding
  assets and revision evidence. Full archive tests caught nine additional missing-file
  failures after the initial import repair, making the archive check essential.
  Existing source ZIPs cannot be silently
  overwritten. Local candidates use an explicit label and record Git provenance.
- `.gitattributes` preserves byte-hashed benchmark, dependency and publication
  evidence files, including existing human-review hashes. The first clean-checkout
  audit exposed older LF Git blobs behind CRLF working files. Those files were
  re-indexed with conversion disabled, preserving the working publication bytes;
  each difference was verified to be line endings only. Original tags are unchanged.
- Fresh runs record individual input and raw/normalized-output hashes. Version 2
  dependency hashing includes tested constraints and publication requirements.
  Resume rejects changed inputs, dependencies or existing evidence.
- Git provenance is captured before output creation. The v2 fixture's producer
  commit is `0d6cb9e`; its existing `dirty: true` field is retained because creation
  of its allowlisted output directory preceded that metadata capture. Its exact
  inputs and raw/normalized outputs are hashed. Later clean checkouts and archive
  manifests identify the complete committed snapshot used for verification.
- The verifier reports per-field metric differences, rejects duplicate run IDs,
  checks human-review hashes and can write audit output outside frozen evidence.
- Recomputation handles serialized execution failures and configured benchmark roots.
- The archive verifier checks every manifest entry and runs the verifier, reviewer
  demo and full Python suite from an isolated extraction with `PYTHONPATH` cleared.
  CI includes these checks after installing documented dependencies.

## Revision validation

Completed locally. Machine-readable evidence: `P0_VALIDATION.json`; complete observed
dependency inventory: `P0_TEST_ENVIRONMENT.txt`. The environment was newly created,
installed from the documented requirements/constraints, and passed `pip check`.

| Check | Verified result |
| --- | --- |
| Fresh offline fixture | 360/360 executions, zero errors, cache disabled |
| Independent metric recomputation | 360/360 rows identical; all 13 integrity checks true |
| Clean Git checkout, `core.autocrlf=true` | Commit `71a2ca3`: 438 passed, zero failures/errors/skips |
| Isolated source ZIP | Commit `3888dd3`, clean when exported: 438 passed, zero failures/errors/skips |
| Source ZIP manifest | All 3,407 declared files verified by byte count and SHA-256 |
| Reviewer demo inside source ZIP | 6/6 passed, including one expected refusal; five MusicXML outputs |
| Human-review evidence | All four original file hashes match in checkout and ZIP |
| Frozen submission baseline | 25 submitted-source files and seven local archive copies preserved |
| Local draft package audit | Passed, including independent revision evidence verification |

Audited source archive: `seraedit-revision-3888dd3-source.zip`, SHA-256
`eb134c1e0fdd91ede44f1cd8630c6d379a8bac0fdc20fc42ce597dacf9013c06`.
It is retained under
`artifacts/softwarex_revision_20261002/source_candidate_3888dd3/`. Detailed execution
logs are under `archive_verification_3888dd3/` in that same artifacts parent. The ZIP
is a source snapshot taken before this completed audit was written; the completed
audit and validation receipt accompany it separately. No new hosted CI run or public
release is claimed.

Fresh fixture: `experiments/softwarex_revision_verification_120_v2`. It remains
`mock_non_formal`, with `formal_results_allowed: false`. No fixture result establishes
model performance. The 1,872 re-indexed historical files differ from their previous
Git blobs only in line endings; their working publication bytes were not changed.

## Other P0 status

- 720-run provenance: development-benchmark regression evidence. The Chinese
  preserve-pitch/tenuto correction used feedback from this same benchmark;
  withholding Gold during generation does not establish held-out generalization.
- Real-model comparison: deferred by the author; no API calls in this repair.
- Validator error-detection experiment: pending, distinct from reproducibility.
- Future real-model protocol: remove answer-side `expected_status` and
  `unsupported_reason` from generation prompts and examine constraint-information
  parity across conditions. Fixture results cannot resolve this design issue.

A new public tag/DOI, hosted CI verification, and journal resubmission are separate
from local repair and require review of the finished artifacts.

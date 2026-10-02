# Response to reviewers — partial working draft, not ready for submission

Manuscript number: SOFTX-D-26-01135

Title: SeraEdit: Reliable Language-Guided MusicXML Editing through Structured Score Patches

Decision date: 1 October 2026

Dear Editor and Reviewers,

Thank you for reviewing our manuscript and inviting a minor revision.

The following responses address completed local reproducibility and provenance
corrections. They use working comment IDs because the author supplied the reports
directly and platform reviewer numbering is not yet verified. The live-model
comparison and validator-detection study are now complete locally; final rendering,
archival publication and P1 responses remain incomplete.

## P0-REPRO / P0-SOURCE / P0-COUNT

**Comments:** The released verifier fails benchmark/dependency/metric checks, six
metric rows disagree, the clean-checkout test count differs, and the source archive
omits required evaluation code.

**Response:** We agree and reproduced these failures in the original `v1.0.0` source.
The published fixture was generated before changes to task definitions and dependency
metadata. The dynamics task gained one constraint, while the meter task changed from
three to nine constraints; the original meter outputs do not satisfy the revised
task. This explains all six differing rows. We retain the original records and report
this inconsistency explicitly rather than replacing their hashes or retroactively
describing the old deposit as reproducible.

We generated a separate offline revision fixture from the corrected, fixed inputs.
All 360 executions completed without execution errors, independently recomputed
metrics match all 360 saved rows, and all 13 integrity checks pass. New manifests
record input and output file hashes; resumption rejects dependency or evidence drift.
Git attributes and byte-preserving indexing keep benchmark and human-review evidence
identical across checkout and source export. The isolated archive check also exposed
and resolved missing evaluation, launcher, packaging and branding files.

In a newly installed Windows 11 / Python 3.12.5 environment, the clean revision
checkout and the independently extracted source ZIP each pass 438 tests with no
failures or skips. The ZIP also passes the six-task offline reviewer demo and
independent evidence verification. The original tag collected 411 tests in our
environment and had one failure caused by ignored local data; we have corrected the
manuscript's test-count statement accordingly. Full provenance, environments and
artifact digests are recorded in the revision audit.

The source ZIP tested here is a local revision candidate. Its publication metadata
and final release links will be updated after the complete revision is ready; the
original DOI continues to identify the original deposit. Hosted CI has been extended
to check the actual source archive, but no new hosted run is claimed in this draft.

**Location:** Section 3 and Table 3; `docs/softwarex/REPRODUCIBILITY.md`;
`P0_REPRODUCIBILITY_REPORT.md`; `P0_VALIDATION.json`. Final rendered page/line numbers
remain pending.

## P0-REGRESSION

**Comment:** The 720/720 replay should be described as regression evidence if the
generator was adjusted using the same benchmark instructions.

**Response:** We agree. The Chinese preserve-pitch/tenuto correction followed
inspection of results on these benchmark instructions. The generator therefore
received development feedback from this benchmark. We now state this explicitly
and describe the 720 runs as deterministic regression replay of 120 tasks with two
language versions and three repetitions. Withholding Gold patches during generation
does not make these tasks a held-out generalization set. We also changed the wider-
selection count from “66 tasks” to “66 runs.”

**Location:** Section 3; reproducibility protocol and reviewer guide.

## P0-LIVE

**Comment:** The paper claims reliable language-guided editing but only demonstrates
fixture/rule-based paths; the implemented three-condition comparison lacks real models.

**Response:** We agree and added a real-provider demonstration using `deepseek-flash`
on 2 October 2026: 120 tasks in each of Full Rewrite, Patch Only and Sera Full,
360 runs total. We freeze code, prompts, task inputs and scoring, retain all raw
responses and repair requests, and reproduce all 360 metric rows offline with 14
integrity checks. The API reports an alias rather than an immutable model snapshot.
Gold patches, scoring constraints and expected-answer labels are excluded from
generation. Both patch conditions receive identical initial prompts/schema; only
Sera Full has bounded repair. Two overlapping development pilots are retained,
including a public assertion-contract clarification made before the main run.

The results qualify the original motivation. Strict editing success, requiring task
constraints, valid MusicXML, complete preservation and an actual non-refused output,
was 72/110 (65.5%), 65/110 (59.1%) and 63/110 (57.3%), respectively. Measured non-target
changes occurred in 17/105, 18/92 and 0/73 produced scores. All conditions correctly
refused the 10 expected-refusal tasks, but Sera Full also refused 34 executable tasks.
We therefore do not claim generally improved editing success from structured patches.
The observed result is a protection/coverage tradeoff; withheld outputs count against
completion. A paired source-cluster analysis and all failures are included.

The abstract, results and limitations now make this qualification explicit. This is
one model alias on a small development benchmark, not a held-out generalization
evaluation or a musical-quality study. Same-initial-response replay also separates
successful repair from refusal: correct outcomes improved from 62/120 to 73/120,
while 25 repaired editing tasks ended in erroneous refusal.

**Location:** Abstract, Sections 3.1 and 4, evidence table;
`DEEPSEEK_RESULTS.md`, `LIVE_EXPERIMENT_PROTOCOL.md` and
`experiments/softwarex_deepseek_core_20261002_v1/`. Final rendered line numbers pending.

## P0-VALIDATORS

**Comment:** The ability of validators to detect errors is asserted but never measured.

**Response:** We added a constructed-error study on 20 existing synthetic
scores, with 180 labeled mutations and 20 canonical-valid controls. The study
preserves the input patches, detector reports, source hashes and rollback checks.
It exposed an ignored `dynamic_equals` postcondition, which we corrected. After
the correction, all 180 invalid patches were rejected and all rejected transactions
returned the original fingerprint. The same-case post-fix test is regression
evidence, and the pre-fix results remain available.

The pipeline also rejected three of the 20 canonical-valid controls because
grace-note dynamics changed during MusicXML round-trip. We report this 15%
end-to-end rejection rate as an export/representation limitation; it is not an
isolated validator false-positive estimate. We distinguish targeted semantic
detection from rejection for an unrelated fault and do not infer real-model error
prevalence or generalization from these constructed cases.

**Evidence:** `VALIDATOR_DETECTION_REPORT.md` and
`experiments/softwarex_validator_detection_200_v1/`. Manuscript Section 3.2 and the
evidence table contain the results; final rendered line numbers remain pending.

## Pending responses

- Literature, platform support, UI evidence, terminology and other P1 points remain
  to be completed before this response is ready for submission.
- The original public release/DOI are unchanged. Revised publication links, final
  page/line references and submission files remain pending.

# Response to reviewers — partial working draft, not ready for submission

Manuscript number: SOFTX-D-26-01135

Title: SeraEdit: Reliable Language-Guided MusicXML Editing through Structured Score Patches

Decision date: 1 October 2026

Dear Editor and Reviewers,

Thank you for reviewing our manuscript and inviting a minor revision.

The following responses address completed local reproducibility and provenance
corrections. They use working comment IDs because the author supplied the reports
directly and platform reviewer numbering is not yet verified. The live-model
comparison, validator-detection experiment and P1 responses remain incomplete.

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

## Pending responses

- P0-LIVE: real-provider comparison deferred at the author's request. No mock or
  rule-based result will be substituted for it.
- P0-VALIDATORS: error-detection/false-rejection experiment remains pending.
- Literature, platform support, UI evidence, terminology and other P1 points remain
  to be completed before this response is ready for submission.

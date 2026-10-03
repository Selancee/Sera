# Response to reviewers — R1 working draft

Manuscript number: SOFTX-D-26-01135

Revised title: SeraEdit: Scoped and Validated Language-Guided MusicXML Editing

Decision date: 1 October 2026

Dear Editor and Reviewers,

Thank you for reviewing our manuscript and inviting a minor revision.

The following responses address completed local reproducibility and provenance
corrections. They use working comment IDs because the author supplied the reports
directly and platform reviewer numbering is not yet verified. The live-model
comparison and validator-detection study are now complete locally;
archival publication and the bridge visual check remain incomplete. Local P1
responses and acceptance status are recorded below.

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
artifact digests are recorded in the revision audit. After the live-protocol and
validator additions, the final source candidate at `ff82c74` passed all 445 tests
in an independent extraction using the same documented Python 3.12.5 dependency
environment. Its 4,299 file hashes, six-task demo, 13 fixture checks and 14 saved
live-evidence checks also passed; the final receipt identifies this later checkpoint.

The source ZIP tested here is a local revision candidate. Its publication metadata
and final release links will be updated after the complete revision is ready; the
original DOI continues to identify the original deposit. Hosted CI has been extended
to check the actual source archive, but no new hosted run is claimed in this draft.

**Location:** Section 3, rendered pages 5–6; the evidence table on page 7;
`docs/softwarex/REPRODUCIBILITY.md`; `P0_REPRODUCIBILITY_REPORT.md`; `P0_VALIDATION.json`.

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
`experiments/softwarex_deepseek_core_20261002_v1/`. Rendered page 6, lines 27–44 and the
results table; page 7, lines 1–16.

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
evidence table contain the results on rendered page 7, lines 17–30 and the table below.

## P1-CONTRIBUTION / P1-LITERATURE

**Comments:** The novelty/impact positioning lacks the code-domain patch-and-test
and instruction-editing lines, the closest symbolic-editing work and MuseScore.
No external editing tool is used as a measured reference.

**Response:** We narrowed the title and explicitly identify three software
contributions: the source-bound scoped ScorePatch contract, an executable reversible
validation workflow, and licensed tasks with reproducible comparison tooling. We
cite SWE-bench (Jimenez et al.), Can It Edit? (Cassano et al.), Not that Groove
(Zhang, 2025 version) and the official MuseScore plugin documentation. We do not
claim to introduce instruction-driven symbolic editing or execution-based evaluation.
The MusicXML-specific integration concerns stable event addresses, fingerprints,
protected scopes, notation invariants and round-trip acceptance. We explicitly state
that these references provide context; no measured performance ranking against
external tools is claimed. The present evidence compares internal system conditions,
with different task/representation contracts preventing a direct cross-paper ranking.

The protection/completion tradeoff is now central to the Abstract and Sections 3–5.
The infrastructure makes failed edits and rejection costs inspectable; it does not
establish musical quality, universal safety, long-horizon agency or a superior model.

**Location:** Revised title, Abstract, Sections 1 and 4–5; references [8–11];
LITERATURE_VERIFICATION.md. Primary records were checked on 3 October 2026.

## P1-PLATFORM

**Comments:** Explain the Windows-only desktop/host boundary, provide POSIX source
installation commands and exact Python/Node/npm environment versions.

**Response:** Section 2.3 and the abstract distinguish Windows desktop/automatic host
integration from the Python reviewer path. INSTALLATION.md now provides POSIX venv,
installation, demo, benchmark and FastAPI commands, with manual MusicXML handoff.
The reviewer reports macOS core execution; we have not independently revalidated
macOS/Linux and do not claim their desktop or automated bridge support. Provider
credentials can be supplied through environment variables rather than the Windows
credential-store UI. C7 records Windows 11 build 10.0.26200, Python 3.12.5, Node.js
24.16.0 and npm 11.13.0. Local-first is defined explicitly; optional remote inference
transmits score context. The tested MuseScore 4.5.2 path uses a saved file and CLI
conversion; it does not export unsaved in-memory changes or implement host undo.

**Location:** Abstract, Sections 2.3 and 3, code metadata entry C7, INSTALLATION.md, USER_MANUAL.md.

## P1-CONSISTENCY / P1-REQUIREMENTS

**Comments:** Unify abstract/keywords, validator membership, condition names,
runs/tasks units and declaration headings; update stale requirements and boundaries.

**Response:** The R1 fill-in sheet takes the exact manuscript abstract and six
keywords. Original August files remain immutable historical records. The eight
checks are named once in Section 2.2; the abstract and cover letter refer to that
contract without competing lists. The condition names Full Rewrite, Patch Only and
Sera Full are mapped to code IDs and former labels. The host-scope result consistently
reports 240 runs, 174 widened and 66 not widened. The declaration heading is
“Declaration of competing interest” in the manuscript and separate statement.
The requirements matrix now identifies the current draft, corrected fixture and
real-provider evidence rather than treating the old failed artifact as passing.

**Location:** R1 manuscript, submission/EDITORIAL_MANAGER_FILL_IN.md,
submission/COVER_LETTER.md, submission/DECLARATION_OF_INTEREST.md,
SOFTWAREX_REQUIREMENTS_MATRIX.md and REPRODUCIBILITY.md.

## P1-UI

**Comment:** Add screenshots or a screencast showing the claimed interface, diffs,
rejection reasons, undo and bridge operation.

**Response:** Figures 2–3 are genuine local source-UI captures showing a valid
proposal with element-change counts/protected-scope status and a rejected instruction
with disabled apply. Additional captured states show an applied revision, an undo
control and an undo revision. The screenshots use local rules and manual MusicXML
import; they are not attributed to the real-model experiment or packaged Electron.
UI_EVIDENCE.md records exact reproduction and the observed wording failure.

**Open item:** The native MuseScore file-picker could not be reliably controlled,
so the full plugin send/open-revision sequence is not visually verified here.
Manual-import screenshots and automated bridge tests do not close this request.
The bridge panel and opened revised score still need a genuine visual capture.

## P1-LICENSE / P1-PUBLICATION

**Comments:** Add SPDX source identifiers, synchronize DOI metadata and rerun hosted CI.

**Response:** The existing root MIT license and dependency notices are retained.
SOURCE_LICENSE_INVENTORY.json gives a file-level SPDX-License-Identifier and SHA-256
for tracked first-party Python/JavaScript/TypeScript sources. We use this sidecar
instead of adding comments to every frozen producer file: modifying those bytes
would invalidate the recorded experiment implementation hashes. This is a reasoned
alternative to the requested inline headers, not a claim that every source has a
new header. Installed dependencies retain their own licenses and are excluded.

publication.yml already identifies the original v1.0.0 version DOI. The revision
explicitly distinguishes the original tag/deposit from the local corrected candidate;
that DOI is not represented as containing new experiments. Local isolated-archive
validation is recorded, while a new hosted CI run and revised public deposit remain
publication gates. No hosted green result or public release is asserted for this branch.

## Remaining submission gates

- Obtain genuine bridge send/open-revision visual evidence.
- Publish the reviewed revision source/data and verify its hosted CI; insert the
  new immutable links without overwriting the original deposit.
- Complete author review and the Editorial Manager assembled-PDF check. Platform
  reviewer numbering and originally uploaded files remain unverified.

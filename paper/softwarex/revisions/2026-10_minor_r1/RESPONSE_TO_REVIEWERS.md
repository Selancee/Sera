# Response to reviewers

Manuscript number: SOFTX-D-26-01135

Revised title: SeraEdit: Scoped and Validated Language-Guided MusicXML Editing

Decision date: 1 October 2026

Dear Editor and Reviewers,

Thank you for reviewing the manuscript and inviting a minor revision. We have
corrected the reproducibility problems, added real-provider and constructed-error
experiments, documented interface and bridge operation, and narrowed the claims
to match the evidence. The revised source and evidence are publicly archived at
https://doi.org/10.5281/zenodo.23117392.

The responses follow Reviewer 1 and Reviewer 2 in the order shown in the peer
review page. Comment summaries are paraphrases; the numbered Weaknesses,
Questions and Suggestions follow Reviewer 1's report. Section, figure and page
references refer to the revised clean manuscript, not the original submission.
Evidence filenames refer to the revision materials and archived research evidence.

## Reviewer 1

Report dated 23 September 2026.

Thank you for checking the released software and identifying the discrepancies.
The responses below follow your Weaknesses, Questions to the Authors and
Suggestions in their original order.

### Weakness 1 Three condition outcomes and external comparisons

Comment summary: The manuscript counts executed cases without reporting per-condition outcomes, and provides no measured external editing baseline.

Response: We agree and added a real-provider demonstration using `deepseek-flash`
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
`experiments/softwarex_deepseek_core_20261002_v1/`. Rendered page 6, lines 21–45 and the
results table; page 7, lines 1–8.

We also revised Section 1 to distinguish contextual literature comparisons from
measured system comparisons. We have not evaluated an external editing tool and
do not claim a performance ranking against one. The present demonstration compares
the three internal conditions on the same tasks; differing musical representations
and editing contracts limit direct cross-paper comparison.

### Weakness 2 Reproducibility failures and test count

Comment summary: The designated release fails benchmark-hash, dependency-hash and metric checks; six rows disagree, and the clean test suite fails and has a different count.

Response: We agree and reproduced the failures in the original v1.0.0 source. The
published fixture preceded changes to task definitions and dependency metadata.
The dynamics task gained one constraint and the meter task changed from three to
nine; the old meter outputs do not satisfy the revised task. This explains the six
disagreeing rows. We preserve those records and report the inconsistency, rather
than relabeling the old deposit as reproducible.

We generated a separate corrected fixture from fixed inputs. Its 360 executions
completed without execution errors, all 360 metric rows were reproduced, and all
13 integrity checks passed. The revision adds Git attributes and byte-preserving
evidence indexing, rejects input or dependency drift on resumption, resolves the
test dependency on ignored local data, and includes the missing evaluation,
launcher, packaging and branding files in the source archive.

The authoritative R1 source and evidence are now archived at
https://doi.org/10.5281/zenodo.23117392, corresponding to revision head
0d319bc381cfc21687adaeff06dcb1f7797b8f18. Hosted CI run 37096317165 passed
447 Python tests in an independently extracted source ZIP, 133 frontend tests,
the production build and 14 saved-live-evidence integrity checks. It verified
4,359 source-file hashes. The CI synthetic merge and revision head have the same
tree. All four public downloads matched the tested artifacts by SHA-256 on
3 October 2026. CI: https://github.com/Selancee/Sera/actions/runs/37096317165.

The manuscript now reports 447 tests for the archived R1 implementation. The
earlier 438- and 445-test checkpoints remain identified separately in the evidence
history. The original tag collected 411 tests in our environment, including one
failure; the original claim of 408 tests is not retained as a verified count.
The original DOI 10.5281/zenodo.22128976 retains its historical meaning. The new
deposit contains a preparation-stage manuscript snapshot; the revised submission
documents update the final citations without altering those archive bytes.

Location: Section 3, pages 5–7 and the evidence table; code metadata C1–C3;
Data and code availability; P0_REPRODUCIBILITY_REPORT.md and
PUBLICATION_VERIFICATION.json.

### Weakness 3 Windows boundary and non Windows access

Comment summary: The desktop and host integration are Windows-specific, while the Python core can run off Windows; the installation path does not explain this distinction.

Response: Section 2.3 and the abstract distinguish Windows desktop/automatic host
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

### Weakness 4 Literature and contribution

Comment summary: The paper omits relevant patch-and-test, instruction-editing and symbolic-music work, and does not cite MuseScore.

Response: We narrowed the title and explicitly identify three software
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

### Weakness 5 Internal consistency

Comment summary: Abstracts, keyword counts, validator membership, condition names and runs/tasks units disagree.

Response: The R1 fill-in sheet takes the exact manuscript abstract and six
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

### Weakness 6 Visual evidence of the interface and bridge

Comment summary: The paper lacks screenshots or video supporting the interface, rejection, diff and bridge claims.

Response: Figures 2–4 now show the actual desktop proposal, rejected source-UI
instruction, and MuseScore rendering the reviewed revision. On 3 October 2026 we
completed the native plugin sequence: save a synthetic score as MSCZ, choose/send
it through Sera Score Bridge 0.3.3, receive it in the Electron development shell,
review/apply a local-rule proposal, and use the plugin to open revision 1 in a
separate MuseScore 4.5.2 window. Eight native captures preserve this
sequence and the Sera undo result. BRIDGE_VISUAL_ACCEPTANCE.json records hashes
and independent XML checks: exactly four target pitches change, all 16 notes retain
duration/voice, and revision 2 restores the original notes.

UI_EVIDENCE.md distinguishes this bridge run from the earlier manual-import browser
captures and retains the observed wording failure. The interface reports operation
summaries and element-change counts; it is not a graphical note-diff viewer.
The before/after host screenshots and saved XML make the demonstrated musical
difference inspectable. This local-rule demonstration does not establish live-model
accuracy, packaged-installer acceptance, musical preference or in-place host undo.

Location: Section 3, Figures 2–4, pages 4–5; UI_EVIDENCE.md and
BRIDGE_VISUAL_ACCEPTANCE.json in the R1 evidence.

### Question 1 Actual model provider

Comment summary: Do any runs use a real provider, and where are the results?

Response: Yes. The revision adds 360 actual DeepSeek runs using the API alias deepseek-flash
on 2 October 2026, with saved raw responses and repair requests under
experiments/softwarex_deepseek_core_20261002_v1/ in the new R1 deposit.
Section 3.1 identifies the model alias, date, frozen producer e3a34e1 and settings.
The earlier fixture and rule runs establish regression behavior, not model accuracy.
The API does not identify an immutable model snapshot. See the detailed answer to Weakness 1.

### Question 2 Metrics and outcomes for each condition

Comment summary: Which metric and result belong to each of the three conditions?

Response: Section 3.1 defines strict editing success as a produced, non-refused score with
valid MusicXML, all task constraints satisfied and complete measured non-target
preservation. In Full Rewrite, Patch Only and Sera Full order, strict success is
72/110, 65/110 and 63/110; leakage is 17/105, 18/92 and 0/73 produced scores;
erroneous editing refusal is 5/110, 10/110 and 34/110. All three correctly refuse
10/10 expected-refusal tasks. Withheld outputs count against editing success.
These results support a protection/completion tradeoff, not overall superiority.

### Question 3 Authoritative permanent artifact

Comment summary: Which release is authoritative and which artifact was verified?

Response: For this revision, use the versioned Zenodo deposit
https://doi.org/10.5281/zenodo.23117392 and its source commit 0d319bc.
C1–C3 now point to that source/evidence snapshot and the immutable GitHub commit.
The exact source ZIP was tested after independent extraction; its public download
was verified against the tested SHA-256. The old v1.0.0 tag and DOI
10.5281/zenodo.22128976 remain historical artifacts and do not contain the new
model experiments. S1–S3 retain the original Windows executable; no new R1
installer is claimed. The original reproducibility claim has been corrected, as
detailed under Weakness 2.

### Question 4 Desktop and host support off Windows

Comment summary: Will the desktop remain Windows-only and how can other notation users access the bridge?

Response: The current packaged desktop and automated host path target Windows. We do not
claim a working automated bridge off Windows or a completed cross-platform port.
Non-Windows users have documented POSIX commands for the Python reviewer demo,
benchmark and FastAPI service, with manual MusicXML export/import into a notation
application. That manual route is distinct from the Windows bridge. Section 2.3
and the abstract now make this limitation explicit; see Weakness 3.

### Question 5 Verified test suite state

Comment summary: Which suite state should be considered verified given the incorrect 408-test claim?

Response: The archived R1 source at 0d319bc passed 447 Python tests without failures or skips
in the isolated-archive hosted CI check. The manuscript distinguishes this result
from the earlier 438- and 445-test revision checkpoints and the original 411-test
collection with a failure. The earlier 408 figure is not represented as verified.
Exact commit, tree and artifact provenance appear in PUBLICATION_VERIFICATION.json
and the archived verification reports.

### Suggestion 1 Release consistency DOI CI and SPDX identifiers

Comment summary: Include missing source, stabilize hashes and fixtures, correct the suite count, populate DOI metadata, pass CI and add SPDX identifiers.

Response: The source-archive, evidence-hash, corrected-fixture and CI changes are described
under Weakness 2, and the authoritative artifact under Question 3. We preserved
the original failed records and published a separate corrected revision.
publication.yml now records the new DOI separately from the old version DOI.

The existing root MIT license and dependency notices are retained.
SOURCE_LICENSE_INVENTORY.json gives a file-level SPDX-License-Identifier and SHA-256
for tracked first-party Python/JavaScript/TypeScript sources. We use this sidecar
instead of adding comments to every frozen producer file: modifying those bytes
would invalidate the recorded experiment implementation hashes. This is a reasoned
alternative to the requested inline headers, not a claim that every source has a
new header. Installed dependencies retain their own licenses and are excluded.

### Suggestion 2 Report the comparison or withdraw it

Comment summary: Provide a real-provider run and per-condition metrics, or remove the comparison claim.

Response: We added the actual-provider demonstration and per-condition results in Section 3.1
(Weakness 1 and Questions 1–2 above). The revised title, abstract, Impact and
Conclusions no longer imply a demonstrated increase in overall editing accuracy.
The work contributes scoped, validated execution and reproducible comparison
infrastructure, with negative outcomes and refusal costs retained.

### Suggestion 3 Position the contribution in the literature

Comment summary: Cite patch-and-test, edit-instruction and symbolic-editing work and MuseScore, and clarify the remaining contribution.

Response: Section 1 and references [8–11] now include SWE-bench, Can It Edit?,
Not that Groove and official MuseScore documentation. We distinguish the
MusicXML-specific combination of stable addressing, source binding, protected
scopes, notation checks and round-trip acceptance from prior instruction editing
and test-based evaluation. No measured external baseline is claimed.
See Weakness 4 for the full positioning.

### Suggestion 4 POSIX instructions and exact environments

Comment summary: Add non-Windows commands, prominently state the Windows boundary and record environment versions.

Response: INSTALLATION.md now provides the POSIX source route. The abstract and Section 2.3
state the desktop/host boundary. Code metadata C7 records Windows 11 build
10.0.26200, Python 3.12.5, Node.js 24.16.0 and npm 11.13.0. We distinguish
documented commands and the reviewer-reported macOS core run from independent
cross-platform validation, which we have not performed.

### Suggestion 5 Consistency and presentation

Comment summary: Unify abstracts, keywords, validators and condition labels; fix units and declaration headings; add screenshots and update requirements.

Response: The revised manuscript and portal fill-in sheet contain the same abstract and six
keywords. Section 2.2 defines the eight checks and maps condition names; the wider
selection result consistently reports 240 runs, with 174 widened and 66 not widened.
Figures 2–4 and the archived UI evidence document actual operation. The requirements
matrix, reproducibility boundaries and Declaration of competing interest heading
are synchronized. See Weaknesses 5–6 for details.

## Reviewer 2

Report dated 28 September 2026.

Thank you for recognizing the transaction design and for identifying the gap
between the original claims and the evidence. We address the three concerns below;
these descriptive headings follow the order of your unnumbered report.

### Real model evidence and three condition comparison

Comment summary: The title and motivation claim reliable language-guided editing, but fixture/rule runs do not demonstrate that claim or report a real-model comparison.

Response: We agree and added a real-provider demonstration using `deepseek-flash`
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
`experiments/softwarex_deepseek_core_20261002_v1/`. Rendered page 6, lines 21–45 and the
results table; page 7, lines 1–8.

We therefore changed the title to “SeraEdit: Scoped and Validated Language-Guided
MusicXML Editing” and define the contribution as the executable editing contract
and reproducible research infrastructure. The new results demonstrate that the
software can support the intended comparison, including unfavorable results.

### Measured validator detection and rejection costs

Comment summary: The ability of validators to detect errors is asserted but not measured.

Response: We added a constructed-error study on 20 existing synthetic
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
evidence table contain the results on rendered page 7, lines 9–22 and the table below.

### Same benchmark development of the rule generator

Comment summary: Was the local generator developed or tuned on the same instructions, including the Chinese preserve-pitch/tenuto correction?

Response: We agree. The Chinese preserve-pitch/tenuto correction followed
inspection of results on these benchmark instructions. The generator therefore
received development feedback from this benchmark. We now state this explicitly
and describe the 720 runs as deterministic regression replay of 120 tasks with two
language versions and three repetitions. Withholding Gold patches during generation
does not make these tasks a held-out generalization set. We also changed the wider-
selection count from “66 tasks” to “66 runs.”

**Location:** Section 3; reproducibility protocol and reviewer guide.

# SoftwareX minor-revision plan — SOFTX-D-26-01135

Created 2 October 2026. Official deadline from the decision email: **31 October 2026**.
Internal packaging target: 25 October, leaving time for author review and the
Editorial Manager PDF workflow. This target is a planning choice, not a journal rule.

## Confirmed scope

The editor requests a minor revision and a response to the platform reviews. On
2 October the author supplied two review texts directly, one as an attachment and
one pasted into chat. Their platform reviewer numbers have not been verified.
The P0 reproducibility repair, authorized DeepSeek comparison and validator study
are complete locally. The author authorized contribution clarification and P1
acceptance work on 3 October 2026. The detailed diagnosis and validation
record are in `P0_REPRODUCIBILITY_REPORT.md`.

| Priority | Work | Current status | Concrete deliverable / acceptance check |
| --- | --- | --- | --- |
| P0 | Preserve submission and software baselines | Completed locally | 25 submission-ready files with Git blob IDs/SHA-256; original public source package and both manuscript archive variants retained; independent revision branch |
| P0 | Verify original Editorial Manager upload | Waiting for login | Read original file list and assembled submission PDF; compare available files to frozen DOCX/PDF; record differences without replacing the baseline |
| P1 | Read received reviewer reports | Received from author | Two supplied texts are available; platform numbering and completeness remain unverified |
| P1 | Build the comment-by-comment plan | P0/P1 mapped | Eight P1 items distinguish completed local work, a license-sidecar alternative, bridge visual evidence and public publication gates |
| P2 | Make the requested minor edits | Local prose and evidence updated | Contributions, real-model tradeoff, literature, Windows boundaries, screenshots and metadata synchronized; see P1_ACCEPTANCE.md |
| P2 | Prepare the response letter | Local working reply generated | Responses cite retained evidence and explicitly identify incomplete bridge/publication work |
| P3 | Validate the revised deliverables | Reproducibility passed; complete submission pending | Latest isolated ZIP passes 445 tests; 13 fixture and 14 live checks; six-task demo; see DEEPSEEK_SOURCE_ARCHIVE_VALIDATION.json |
| P3 | Author review and resubmission preparation | Pending completed revision | Final response, clean DOCX/PDF, marked copy, declarations and change summary ready; author reviews assembled portal PDF before final submission |

## Remaining review work

- Real-provider three-condition experiment: completed, 360 runs with retained failures.
- Validator mutation/detection evaluation: completed, 200 constructed cases.
- 720-run benchmark-feedback disclosure: documentation, R1 manuscript and partial
  response corrected and synchronized with the completed reproducibility audit.
- Literature, contribution, platform and editorial consistency: locally addressed in P1.
- Actual UI proposal, apply, undo and rejected wording captured; native bridge send/open visual sequence remains unverified.
- Revised public archive/DOI/hosted CI, author review, marked manuscript and portal PDF remain submission gates.

## Review processing

1. Save the full reports locally and retain their provenance. Populate
   `REVIEWER_COMMENT_MATRIX.csv` with original comments, not guessed requirements.
2. Distinguish text clarification, documentation correction, software correction,
   evidence clarification, and requested new evaluation. Each item gets an explicit
   deliverable and a check that can actually establish completion.
3. Perform small text/metadata corrections first. For code or experiment requests,
   preserve existing evidence and produce separately named outputs from real runs.
4. Keep the reliability-engineering scope of this SoftwareX manuscript. Retain the
   distinction between deterministic product acceptance, mock runner checks, the
   same-reviewer benchmark inspection, live-LLM performance, and musical preference.
5. Write response text after the corresponding change is completed. A proposed test
   or future experiment must not be described as executed.

## Working and archival boundaries

- Baseline: `paper/softwarex/baselines/submission_2026-08-28/` is frozen.
- R1 Markdown authority: `paper/softwarex/revisions/2026-10_minor_r1/manuscript/seraedit_softwarex.md`.
- The R1 Markdown began byte-identical to the original. Changes follow the supplied
  review texts; final DOCX/PDF generation follows completion of the evidence changes.
- The release tag `v1.0.0`, public Release assets and Zenodo DOI are retained.
  The current checkout contains post-submission UI fixes and is not the deposited
  1.0.0 software snapshot. Decide whether a new software version is needed only
  after the requested changes are known.
- New verification reports go under `artifacts/softwarex_revision_20261002/`; do not
  overwrite the existing publication experiment summaries or submission reports.

## Checks available now

```powershell
.\.venv\Scripts\python.exe scripts\verify_softwarex_revision_baseline.py --include-local-archives
.\.venv\Scripts\python.exe -m pytest tests\test_softwarex_revision_baseline.py tests\test_submission_metadata.py tests\test_prepare_softwarex_submission_assets.py tests\test_softwarex_package_verifier.py
.\.venv\Scripts\python.exe scripts\verify_softwarex_package.py --profile submission --output artifacts\softwarex_revision_20261002\pre_revision_submission_check.json
```

## Completion gates

- All actual comments captured, mapped, answered, and tied to a completed change or
  reasoned response; no inferred review request presented as received.
- Original submitted files verified from the platform when accessible; remaining
  uncertainty explicitly retained if the platform cannot expose them.
- Revised prose, change-marked copy, response letter and evidence agree.
- Frozen baseline and deposited version remain intact.
- Final upload/submission follows the author's review of the concrete revision package.

Browser retrieval was unsuccessful. The author subsequently supplied review text
directly, enabling this repair independently of portal access. Original uploaded
files and final portal reviewer numbering remain unverified.

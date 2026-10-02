# SoftwareX minor-revision plan — SOFTX-D-26-01135

Created 2 October 2026. Official deadline from the decision email: **31 October 2026**.
Internal packaging target: 25 October, leaving time for author review and the
Editorial Manager PDF workflow. This target is a planning choice, not a journal rule.

## Confirmed scope

The editor requests a minor revision and a response to the platform reviews. The
email provides no reviewer-specific requests. Consequently, the table below is the
execution plan for receiving and handling those requests; it is not a fabricated
summary of reviewer criticism. No new LLM experiments, human study, architectural
refactor or musical-quality claim is automatically added to this revision.

| Priority | Work | Current status | Concrete deliverable / acceptance check |
| --- | --- | --- | --- |
| P0 | Preserve submission and software baselines | Completed locally | 25 submission-ready files with Git blob IDs/SHA-256; original public source package and both manuscript archive variants retained; independent revision branch |
| P0 | Verify original Editorial Manager upload | Waiting for login | Read original file list and assembled submission PDF; compare available files to frozen DOCX/PDF; record differences without replacing the baseline |
| P1 | Read all editor/reviewer reports | Waiting for login | Capture full text with reviewer and comment IDs, including separate reports; verify no report or page is omitted |
| P1 | Build the comment-by-comment plan | Pending reports | One matrix row per actual comment: original wording, interpretation, proposed edit, affected files/sections, evidence needed, completion status |
| P2 | Make the requested minor edits | Pending mapped comments | Edit only the R1 working manuscript; record precise before/after text and associated comment ID; update figures/docs/code only where a real request requires it |
| P2 | Prepare the response letter | Template created | Answer every sourced comment; cite the final section/page/line and completed evidence; explain any unimplemented request with a concrete reason |
| P3 | Validate the revised deliverables | Baseline passed; revision checks pending | 25 frozen files and seven local archives verified; 28 focused tests and the original 41-file submission check passed; clean/marked revision checks follow actual edits |
| P3 | Author review and resubmission preparation | Pending completed revision | Final response, clean DOCX/PDF, marked copy, declarations and change summary ready; author reviews assembled portal PDF before final submission |

## Once the reports are accessible

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
- The initial R1 Markdown is byte-identical to the original. No revised DOCX/PDF has
  been generated yet because the actual comments are unavailable.
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

The author selected the Codex in-app Browser. Its visible tab could not navigate to
Editorial Manager because the browser could not verify saved access permissions.
Restore that browser's access first, then sign in and retrieve the reports. Do not
substitute a different browser for the selected login session. Baseline preservation
and workspace preparation have been completed independently of this access blocker.

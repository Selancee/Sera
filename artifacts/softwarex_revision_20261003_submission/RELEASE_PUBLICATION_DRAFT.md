# SeraEdit SoftwareX R1 source and evidence archive

Proposed release title: SeraEdit SoftwareX R1 source and evidence revision.
Proposed new Git tag: softwarex-r1-20261003.
Repository: https://github.com/Selancee/Sera.
Revision branch: codex/softwarex-minor-revision-20261002.
Proposed code/test head: 0d319bc381cfc21687adaeff06dcb1f7797b8f18.
Hosted CI: https://github.com/Selancee/Sera/actions/runs/37096317165 (both jobs passed; downloaded archive hashes verified).

This is a source and evidence revision, not a newly built desktop installer. The existing v1.0.0 executable remains the historical installer. Preserve v1.0.0 and DOI 10.5281/zenodo.22128976; add a new revision archive with an immutable record identifier only after author authorization. No new tag, GitHub Release, Zenodo draft or record has been created by this plan.

## Draft public description

SeraEdit makes language-guided MusicXML edits source-bound, scoped and reviewable through ScorePatch transactions, deterministic validation and reversible execution. This revision preserves the original software deposit and adds corrected reproducibility fixtures, saved DeepSeek three-condition results, a constructed-error detector study, and native MuseScore bridge evidence.

The real-model demonstration reports strict editing success of 72/110, 65/110 and 63/110 for Full Rewrite, Patch Only and Sera Full. Sera Full has zero measured non-target changes among 73 output scores but erroneously refuses 34 executable tasks. These are development-benchmark results demonstrating a protection/completion tradeoff, not a claim of overall superiority or held-out generalization. All stored model outputs can be rescored without a new API call.

Code license: MIT. Synthetic benchmark: CC0-1.0. Dependencies retain their own licenses. Author: Yuan Gao; affiliation and ORCID remain those of the submitted manuscript. A file-level SPDX sidecar preserves frozen producer bytes and is described explicitly as an alternative to inline license headers.

## Publication sequence pending author authorization

1. Verify the final hosted run and the downloaded archive hashes; freeze the source snapshot and attach its manifests and verification receipts.
2. Prepare a separate revision deposit using the existing record versioning workflow after authenticated access is available. Do not invent or reuse a DOI for new data.
3. Update C1-C3 and the data/code statement with actual new identifiers; retain an explicit historical executable boundary in S1-S3. Regenerate and inspect clean/highlighted manuscripts, response and statements.
4. Publish the approved new archives, verify their public downloads, then complete the journal revision form and assembled-PDF review. Final journal submission is a separate author approval.

## Verified candidate artifacts

The hosted archive records synthetic PR merge a8535862f537ac91ea1331b94a29202908a3ca84, whose tree equals revision head 0d319bc381cfc21687adaeff06dcb1f7797b8f18. Main was not merged. Preserve this checkout provenance when publishing the exact CI bytes.

- seraedit-ci-candidate-softwarex-manuscript.zip: SHA-256 `1b5b12054c23a1d95a93a61a1d229b34733947d81dfea334964f6a7a8da2f391`; 2285218 bytes.
- seraedit-ci-candidate-source.zip: SHA-256 `c20fde8c679c0e073aae0c9ec6613943a1904e75c3546d1fd8cb1f52915edd4a`; 17225942 bytes.

Acceptance: 447 isolated Python tests, 133 frontend tests, 14 saved-live-evidence checks, 4,359 source member hashes and 95 manuscript member hashes. All passed. See CI_ACCEPTANCE_0d319bc.json. New identifiers must be verified after an independently authorized publication; existing DOCX statements still need those links.

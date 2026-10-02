# R1 change log

## 2 October 2026 — preparation

- Read the actual Gmail decision: minor revision, due 31 October 2026.
- Retained 25 submission-ready files from commit `a21acbe`; created byte hashes and
  Git provenance. Exact Editorial Manager uploads remain pending portal verification.
- Preserved software `v1.0.0`, submission-ready and pre-revision source snapshots,
  and both local/published manuscript ZIPs. Documented their provenance differences.
- Created an independent revision branch, plan, response template and empty comment
  matrix. Started an unchanged Markdown working copy.
- Added a read-only baseline checker that detects file modification, deletion and
  path escape; local archive checks are optional for other checkouts.
- Manuscript content changes: **none yet**. Experiment/metric changes: **none**.
- Reviewer-specific work: pending full reports in authenticated Editorial Manager.
- Verification: 25/25 frozen files and 7/7 local archive copies passed SHA-256/size
  checks; 28 focused tests passed; the 41-file original submission package check
  passed. No experimental result was recomputed or replaced.
- Opened the author's selected in-app Browser panel. Journal navigation is blocked
  by unavailable saved-permission verification; the visible tab is still blank.
  The full reports have not been read and the specific edit plan remains pending.

## 2 October 2026 — completed local reproducibility repair

- The author supplied two actual reviewer texts. Reproduced the original tag's
  three failed verifier checks, six metric differences and ignored-data test failure.
- Fixed source archive omissions and Git byte preservation; added input/output
  hashes, drift-safe resume, detailed metric diagnostics and isolated archive CI.
- Generated a separately named 360-case offline fixture and verified all saved
  metric rows and all 13 integrity checks. The original fixture remains historical.
- A fresh documented dependency installation passed `pip check`; clean checkout
  and isolated source ZIP each passed 438 tests. The source ZIP reviewer demo passed
  6/6 and produced five host-openable revisions. See `P0_VALIDATION.json` for exact
  source revisions and SHA-256, and `P0_REPRODUCIBILITY_REPORT.md` for the diagnosis.
- Revised Section 3 and Table 3 with actual counts and explicit development-benchmark
  provenance for the 720-run rule replay. Populated partial reviewer responses and
  the P0 comment matrix. No revised DOCX/PDF or final response is ready yet.
- Live-model comparison is deferred by the author. Validator-detection evaluation
  and P1 items remain pending. No public tag, DOI update, push or submission occurred.

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

## 2026-10-02 — Completed real-provider comparison and local revision evidence

- User-level DEEPSEEK_API_KEY authenticated; values remain environment-only. Retained both live pilots and froze answer_blind_v3 at clean producer e3a34e1 before core.
- Core completed 360/360 initial runs plus 43 repair calls, all deepseek-flash / stop, without provider failures. All 360 metrics recompute exactly and all 14 integrity checks pass.
- Strict editing success: Full Rewrite 72/110, Patch Only 65/110, Sera Full 63/110. Measured leakage: 17/105, 18/92, 0/73 produced scores. Sera Full erroneously refused 34 executable tasks; results do not establish overall accuracy improvement.
- Offline same-response repair replay: correct outcomes 62/120 to 73/120; 11 improvements, zero regressions, 25 repaired editing tasks ending in erroneous refusal. Added analyze_softwarex_repairs.py so legacy valid-or-refused repair_success is not misreported as editing success.
- Full v3 Python suite: 445 passed, no failures/errors/skips. Packaging-focused tests: 8 passed. Main estimated cost USD 1.0317027, total including pilots USD 1.1044263, not an invoice.
- Updated only the R1 manuscript/response/matrix and result report; original submission/release evidence retained. Added live evidence and all fingerprinted evaluation Python files to candidate source export and an offline live-evidence check to isolated ZIP verification.
- New source-candidate verification follows. P1 revisions, final rendering and revised publication remain pending; no public push, release, DOI update or journal submission.

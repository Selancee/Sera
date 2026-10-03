# SoftwareX revision requirements matrix

Updated 3 October 2026. The active draft is
`paper/softwarex/revisions/2026-10_minor_r1/`; August submission files are historical.
Local verification is distinct from public release, hosted CI and journal submission.
The current journal guide returned HTTP 403; see R1 LITERATURE_VERIFICATION.md for
the retained guide limits and conservative local targets, not a new live confirmation.

| Requirement | Revision evidence | Status |
| --- | --- | --- |
| Software contribution and claim boundaries | R1 Abstract, Sections 1, 4, 5 | Scoped transactions and evaluation infrastructure; no overall accuracy superiority |
| Main text / abstract / keywords | R1 manuscript and fill-in sheet; P1 verifier | Target <=3000 / <=250 / six; exact synchronized fields |
| Permanent release identity | publication.yml; R1 availability statement | Original v1.0.0/DOI retained; revised deposit pending |
| Reproducibility | ff82c74 source archive receipt | 4299 files; 445 tests; reviewer demo 6/6; fixture 13/13; live 14/14 |
| Original evidence failures | P0_REPRODUCIBILITY_REPORT.md | Three original checks failed; separately corrected fixture, original retained |
| Real comparison | DEEPSEEK_RESULTS.md; 360 saved runs | Strict edits 72/65/63 of 110; refusals and coverage disclosed |
| Validator measurement | VALIDATOR_DETECTION_REPORT.md | 180/180 invalid rejected after fix; 3/20 valid-control round-trip rejections |
| Deterministic replay provenance | R1 Section 3 | 720 runs are development regression; 240 host-scope runs include 174 widened and 66 not widened |
| Human review | softwarex_human_review_120_v1 | 120 primary +30 repeat; same reviewer, no independent/aesthetic claim |
| Platform and environment | INSTALLATION.md; R1 Section 2.3 and C7 | Windows versions explicit; POSIX source commands, no verified non-Windows desktop/bridge |
| Literature | LITERATURE_VERIFICATION.md | Code editing, instruction-driven symbolic editing and MuseScore cited; no cross-system performance ranking |
| UI evidence | R1 figures and UI_EVIDENCE.md | Actual local-rule UI states; bridge evidence classified separately |
| Source license attribution | R1 SOURCE_LICENSE_INVENTORY.json | File-level SPDX identifiers and hashes in sidecar; dependency licenses unchanged |
| Final manuscript rendering | R1 manuscript DOCX and render audit | Must pass visual QA; original render not reused as revision proof |
| Hosted CI | .github/workflows/research-ci.yml | Defined; new revision hosted run not claimed until published |
| Journal status | Decision record | Minor revision; deadline 31 October 2026; final submission pending author review |

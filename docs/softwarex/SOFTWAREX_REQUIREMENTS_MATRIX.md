# SoftwareX requirements matrix

This matrix maps the SoftwareX journal page, v4 article structure, and reviewer form
rechecked on 2026-08-27 to auditable project artifacts. `Prepared` means locally
complete; it does not imply a public release.

| Requirement | Evidence | Status |
| --- | --- | --- |
| Original Software Publication structure | `paper/softwarex/manuscript/seraedit_softwarex.*` | Prepared |
| Main text no more than 3000 words | `scripts/verify_softwarex_package.py` | Automated |
| Abstract about 100 words, no more than six keywords | Manuscript + verifier | Prepared |
| C1-C9 code metadata | Manuscript metadata table | Prepared with C2/C3/C9 pending public values |
| Open-source license | Root `LICENSE`, `THIRD_PARTY_NOTICES.md` | MIT selected; owner confirmation pending |
| Public inspectable source | `https://github.com/Selancee/Sera` | Blocked: unauthenticated 404 |
| Permanent archived release | C3 / `publication.yml` | Blocked: DOI not minted |
| Build and operating environment | `docs/softwarex/INSTALLATION.md` | Prepared |
| User manual and illustrative example | `docs/softwarex/USER_MANUAL.md` | Prepared |
| Developer/API documentation | `docs/softwarex/API_REFERENCE.md` | Prepared |
| Automated tests | Python + Vitest suites | Passed on 2026-08-24 |
| Reproducible evaluation | `experiments/softwarex_verification_120_v1` | Passed; mock/non-formal |
| Product runtime acceptance | `experiments/softwarex_runtime_acceptance_720_v4` | 720/720; bilingual x3; source-preserving host round-trip with staff-safe MusicXML voice mapping; non-formal |
| Host-selection localization robustness | `experiments/softwarex_host_scope_robustness_240_v3` | 240/240; source-preserving host round-trip with staff-safe MusicXML voice mapping; 174 widened-selection runs passed |
| Human task/Gold review | `experiments/softwarex_human_review_120_v1` | 120/120 primary reviews and 30/30 stratified repeat checks; zero stale records; same pseudonymous reviewer, so no inter-rater claim |
| End-user review screen | Not required by the SoftwareX article structure | Kept as optional source-level research tooling; hidden in ordinary builds unless `VITE_SERA_ENABLE_RESEARCH_REVIEW=true` |
| Component diagram | `paper/softwarex/figures/figure1_architecture.*` | Prepared |
| Experimental setting and limitations | Manuscript Sections 3-5 | Prepared |
| Dependency/license inventory | `paper/softwarex/dependency_licenses.*` | Prepared after generator run |
| Citation metadata | `CITATION.cff`, `codemeta.json` | Prepared with author placeholders |
| Cover letter and declarations | `paper/softwarex/submission/` | Prepared with identity placeholders |
| Reviewer-oriented final audit | `scripts/verify_softwarex_package.py --profile submission` | Technical and human-review evidence pass; author/public-release fields remain required before upload |

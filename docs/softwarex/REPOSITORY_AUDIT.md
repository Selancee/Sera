# SoftwareX repository audit

Audit date: 2026-08-23  
Baseline commit: `b4eb13921bcbc48a95136cc744cabc094112a541`  
Working tree at audit: dirty (386 entries), so publication packaging must use an
explicit manifest instead of assuming the Git worktree is a release.

## Scope and scientific purpose

SeraEdit is research software for reliable local MusicXML editing. A host score
is imported into a canonical `ScoreDocument`; a natural-language instruction is
converted to a versioned `ScorePatch`; layered validators and an atomic transaction
either produce a reviewable MusicXML revision or reject the change. The scientific
scope is reliability and reproducibility of local symbolic-score editing, not
general music generation or a claim to replace professional notation software.

## Reusable implementation

| Requirement | Repository implementation |
| --- | --- |
| Canonical score model and stable event IDs | `backend/services/score_document_service.py` |
| Versioned patch and scope model | `sera_edit/domain/score_patch.py`, `score_scope.py` |
| Fingerprints | `sera_edit/domain/fingerprints.py` |
| Layered validation | `sera_edit/validation/` |
| Atomic apply/rollback/diff/undo | `sera_edit/execution/` |
| Provider abstraction and mock path | `sera_edit/providers/` |
| Three evaluation conditions | `evaluation/conditions/` |
| Resumable runner and deterministic metrics | `evaluation/runners/`, `evaluation/metrics/` |
| Local desktop and MuseScore bridge | `electron/`, `integrations/musescore/` |

## Verified assets

- 20 CC0 synthetic source scores and 120 task definitions are present.
- `scripts/validate_benchmark.py --split core` passes 120/120 automatic checks.
- All 120 tasks remain marked `pending_human_review`; this is a declared dataset
  limitation, not a hidden completion claim.
- A fresh `softwarex_verification_120_v1` run completed 360/360 mock-fixture
  pipeline cases without execution errors. It is explicitly non-formal and cannot
  support claims about LLM quality.
- Current source regression, frontend tests/build, and packaged Windows runtime
  are recorded in `paper/softwarex/VERIFICATION_REPORT.md`.

## Licensing and rights

- The root software license was absent at audit and has been added as MIT for the
  SoftwareX release track.
- Benchmark fixtures already carry CC0-1.0.
- Audited direct dependencies are permissive; PyInstaller is used under its
  bootloader distribution exception. See `THIRD_PARTY_NOTICES.md`.
- No third-party score, font, model weight, or audio asset is required in the
  source distribution.
- The copyright owner must confirm the MIT choice and that every contributor has
  authority to license their contribution before the repository is made public.

## Publication blockers owned by the author

1. The configured GitHub URL returns 404 to an unauthenticated reader even though
   authenticated `git ls-remote` succeeds; the repository is not publicly inspectable.
2. Author name, affiliation, ORCID, support email, funding and CRediT roles are not
   available in the repository and remain placeholders.
3. No immutable public release tag and no Zenodo/Code Ocean DOI exist yet.
4. The 120 benchmark tasks require human music review if used as a research dataset.

These blockers do not prevent local technical preparation, but they prevent an
honest `submission_ready` verdict.

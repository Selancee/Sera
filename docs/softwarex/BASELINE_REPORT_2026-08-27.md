# SeraEdit private-upload baseline — 2026-08-27

## Candidate

- Version: `1.0.0-dev.14`
- Branch before upload: `main`
- Previous remote baseline: `b4eb13921bcbc48a95136cc744cabc094112a541`
- Intended destination: existing private `Selancee/Sera` GitHub repository
- Public-release status: deliberately disabled for this upload

## Executed checks

| Check | Result |
| --- | --- |
| Python regression | 404/404 passed |
| Frontend regression | 72 files, 120/120 passed |
| Frontend production build | 216 modules transformed; passed |
| Core benchmark validation | 120/120 valid; 0 invalid |
| Frozen human-review evidence | 120 primary, 30 repeated checks, 0 stale |
| SoftwareX draft verifier | passed |
| V0.93 source baseline | notation/export/layout/musicality checks passed |
| Packaged backend and readiness wait | passed |
| Compatibility launcher and Electron startup | passed |
| `compound_001` expanded host scope | only explicit measure 2 changed |
| `meter_001` source-preserving round trip | 3/4, six intended deletions, valid |
| `voice_010` and `voice_004` round trip | only staff-1 measure 3 changed; lower staff stable |

The V0.93 source-only baseline reported `backend_preview_render_success_rate=0.0`
because that optional source process had no notation renderer attached. This is not treated
as a pass: the release boundary was instead exercised by the packaged MuseScore-compatible
MusicXML export/re-import smoke, which passed.

## Upload safety checks

- Anonymous access to `https://github.com/Selancee/Sera` returned HTTP 404 before upload.
- Authenticated `git ls-remote` resolved the existing private remote.
- `.env`, runtime sessions, caches, local projects, build products and old distribution
  archives are ignored and are not part of the candidate commit.
- Only `.env.example` placeholders are included; no API key or private-key signature was
  found by the staged-content scan.
- No candidate file reaches GitHub's 100 MB per-file limit.

## Evidence boundary

This is a software/regression baseline and a private preservation upload. It is not a
formal remote-LLM comparison, does not establish independent inter-rater reliability, and
does not make the repository public or satisfy the eventual SoftwareX public-archive gate.

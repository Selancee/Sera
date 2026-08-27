# Contributing to SeraEdit

Contributions should preserve the canonical ScoreDocument, source fingerprint,
target/protected scope, atomic rollback, and MusicXML round-trip boundaries.

1. Open an issue describing the operation, validator, host, benchmark or documentation
   change and its expected invariant.
2. Work on a focused branch and do not commit API keys, private scores, model weights,
   user settings, or generated build directories.
3. Add unit or integration tests for behavioral changes. Unsupported operations should
   fail explicitly rather than silently succeed.
4. Run Python tests, frontend tests/build, benchmark validation and the draft SoftwareX
   verifier documented in `docs/softwarex/INSTALLATION.md`.
5. Update user/developer documentation and the relevant implementation log.
6. Submit a focused pull request with reproduction steps, before/after behavior, test
   evidence, license/provenance for any new asset, and an explicit statement about
   backward compatibility.

Synthetic benchmark additions must be original or demonstrably public domain/CC0 and
must declare target/protected scope, deterministic constraints, expected status, source
license, and review status. Human musical review is separate from automatic validation.

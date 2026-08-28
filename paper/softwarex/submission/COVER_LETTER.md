[DATE]

Editors-in-Chief  
SoftwareX

Dear Editors,

Please consider our Original Software Publication, “SeraEdit: Reliable
Language-Guided MusicXML Editing through Structured Score Patches,” for SoftwareX.

SeraEdit addresses a reproducibility and safety problem in symbolic-music research:
language-guided editing commonly exposes a complete MusicXML document to unconstrained
rewriting, making unintended changes hard to detect. The software instead represents
an edit as a source-bound, scoped ScorePatch and validates schema, score structure,
exact duration, notation relations, protected content, and MusicXML round trips inside
an atomic transaction. The distribution includes a desktop demonstration, MuseScore
bridge, 20 synthetic CC0 source scores, 120 editing tasks, three experimental
conditions, deterministic metrics, resumable runners, automated tests, and an offline
verification fixture.

For review, a single offline command exercises six representative success/refusal
tasks through proposal generation, validation, transaction commit, source-preserving
MusicXML export, re-import, and evidence reporting. The same checks run in the included
Windows continuous-integration workflow, without an API key or network service.

The manuscript clearly separates verified software behavior from unverified model or
aesthetic claims. The included mock-fixture experiment establishes reproducible
pipeline execution only; it is not reported as LLM performance. This distinction,
together with auditable rejection reasons and protected-scope validation, makes the
software useful for controlled research on reliable notation-editing agents.

The immutable tagged release is available at
https://github.com/Selancee/Sera/releases/tag/v1.0.0. The matching public Zenodo
software deposit is available at https://doi.org/10.5281/zenodo.22128976. The code is
released under the MIT License and the synthetic benchmark under CC0-1.0.

The sole author confirms that this manuscript is original and is not under
consideration elsewhere.

Sincerely,

Yuan Gao

Zhejiang Conservatory of Music

selanceg@gmail.com

# Sera Composer Knowledge Base V0.4

This directory now has two deliberately separate layers:

- `style_knowledge.v0.2.json`: seven compact style profiles used by the deterministic realizer and critics;
- `knowledge_registry.v0.4.json` plus `packs/*.jsonl`: a scalable corpus of atomic rule cards used by retrieval.

The complete V0.4 corpus stays local. For each request, Sera ranks cards against the current score facts, detected source texture, requested style, host instrumentation, target measures, meter, mode, and creative goal. It sends at most the configured card count and token budget to the planner; it never sends the full repository.

Content policy:

- All prose is an original engineering summary written for Sera.
- No textbook passage or copyrighted score excerpt is stored here.
- The profiles are planning and evaluation priors, not claims of universal style correctness.
- Future corpus-derived statistics must identify a public-domain or licensed source and keep source attribution separate from user scores.

The V0.4 corpus provides:

- atomic harmony, melody, motif, phrase, rhythm, form, orchestration, playability, style, Huron-inspired expectation, texture-recognition, and composition-craft rules;
- stable rule IDs, pack IDs, provenance, and a corpus fingerprint;
- explicit style, mode, instrument, goal, meter, and domain metadata;
- deterministic metadata/lexical ranking, domain diversity, and token budgeting;
- a compact evidence object that records which cards were selected and why.

Run `python scripts/build_composer_knowledge_v04.py` to reproducibly rebuild the checked-in packs. Run `python scripts/validate_composer_knowledge.py` to validate the registry, every card, duplicate IDs, fingerprint, corpus counts, and a budgeted retrieval smoke. New packs may be appended to the registry without changing the prompt contract.

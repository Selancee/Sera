# SeraEdit: Reliable Language-Guided MusicXML Editing through Structured Score Patches

> Conference-neutral short-paper draft. The current Core run uses a deterministic mock fixture; every quantitative result below remains an explicit placeholder until a live-model experiment and human benchmark review are complete.

## Abstract

Natural-language score editing is attractive for notation workflows, but asking a language model to rewrite an entire MusicXML document can damage unrelated notes, voices, and notation relations. We present SeraEdit, a language-guided editing layer built around a canonical score document and a versioned, source-bound ScorePatch. Each patch declares target and protected scopes, stable event identifiers, preconditions, and typed operations. A transactional pipeline validates schema, structure, measure duration, notation relations, protected content, and MusicXML round trips before committing, with bounded repair and explicit refusal on failure. We define a 120-task benchmark protocol spanning pitch, rhythm, harmony, voice, notation, structure, compound, and conflicting edits, and compare full-score rewrite, patch-only, and the complete pipeline using deterministic task and preservation metrics. **[RESULT TO BE INSERTED FROM FORMAL LIVE EXPERIMENT.]** The current implementation and mock run establish reproducible experimental plumbing but do not constitute model-performance evidence.

## 1. Introduction

MusicXML is an open interchange format for digital sheet music, but valid XML alone does not guarantee that a local edit preserved musically unrelated material. Recent language models can process symbolic representations, while published evaluations continue to find limitations in multi-step musical reasoning. Existing symbolic-music work predominantly studies understanding or generation; instruction-driven granular editing remains comparatively underexplored.

SeraEdit treats model output as a proposed edit transaction rather than a replacement score. Its contributions are limited to:

1. a versioned structured ScorePatch bound to a canonical source fingerprint;
2. a validation, protected-scope, repair/reject, and transactional application pipeline;
3. a paired benchmark protocol comparing full rewrite, patch only, and the complete pipeline.

## 2. Related Work

MusicXML provides the exchange representation, while toolkits such as music21 demonstrate programmatic access to symbolic scores. ChatMusician and later evaluations investigate how language models understand and generate textual symbolic music, but do not establish preservation guarantees for scoped MusicXML edits. *Not that Groove* directly studies zero-shot instruction-driven MIDI drum editing and uses programmatic tests, providing a close editing-oriented comparison; SeraEdit instead focuses on staff notation, MusicXML round trips, source binding, protected scopes, and transactional rollback. CodeEditorBench motivates separating editing from generation and evaluating task-specific correctness rather than fluency alone.

## 3. Method

### 3.1 Canonical score and scope

MusicXML is imported into one authoritative `ScoreDocument`. Stable `sera-event-id` values, exact rational/tick positions, and SHA-256 fingerprints link the imported document, patch, preview, applied result, playback, and export. `ScoreScope` deterministically selects measures, parts, staffs, voices, event IDs, time ranges, and exclusions. A separate protected scope defines content that must remain unchanged.

### 3.2 ScorePatch and transaction

A ScorePatch contains its schema version, source score/fingerprint, instruction, target/protected scopes, preconditions, expected effects, provenance, and typed operations. Version 1 supports transpose, pitch/duration changes, insertion/deletion, dynamics/articulations, ties/slurs, key/meter changes, voice movement, motif duplication, chord replacement, and batch operations. Unsupported operations are rejected rather than approximated.

Application follows: fingerprint check → schema validation → selector/precondition validation → cloned apply → structural/duration/notation validation → protected-scope comparison → MusicXML round trip → commit or rollback. Deterministic formatting repairs run first; at most two model repair requests may follow. Every attempt and added cost is retained.

## 4. Evaluation Protocol

The Core benchmark protocol contains 120 tasks over 20 short synthetic or license-safe source scores, with ten categories and explicit target/protected scopes. Automatic validation currently passes all 120 generated tasks; all 120 remain marked `pending_human_review`, so the benchmark is not yet described as human-verified.

The paired conditions are: (A) complete MusicXML rewrite; (B) ScorePatch generation with schema parse and basic application only; and (C) the complete SeraEdit pipeline. Metrics include MusicXML validity, patch parse rate, deterministic constraint satisfaction, task success, non-target preservation, operation minimality, element-change precision, refusal accuracy, repair success, latency, tokens, and estimated cost. Planned statistics use task-level paired bootstrap intervals, exact McNemar tests for binary outcomes, Wilcoxon signed-rank tests for continuous/proportional outcomes, effect sizes, and Holm correction.

## 5. Results and Analysis

**[RESULT TO BE INSERTED FROM FORMAL LIVE EXPERIMENT.]**

The repository currently contains a 360-run mock fixture check (120 tasks × 3 conditions). It verifies execution, caching, resume, raw/normalized evidence, metric recomputation, statistics, and asset generation. Its scores and timing must not be cited as language-model performance.

## 6. Limitations and Conclusion

The benchmark uses short symbolic excerpts and does not measure engraving quality, composition quality, or broad aesthetic value. Human task review and cross-application MusicXML testing remain necessary. Provider versions may change, protected-scope fingerprints cannot capture every visual-layout preference, and bounded repair may still reject feasible edits. SeraEdit is therefore positioned as an editing and collaboration layer over professional notation environments, not as a replacement for MuseScore, Sibelius, or musical judgment.

## References

See `references.bib`. Source notes and verification links are recorded in `RELATED_WORK_NOTES.md`.

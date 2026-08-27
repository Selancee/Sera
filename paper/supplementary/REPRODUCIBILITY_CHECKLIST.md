# Reproducibility checklist

- [x] Versioned ScorePatch schema and prompt hashes.
- [x] Fixed benchmark split and content hash.
- [x] Source, target, and protected scopes recorded per task.
- [x] Gold patch or explicit refusal target per task.
- [x] Deterministic constraint and preservation metrics.
- [x] Three separated experimental conditions.
- [x] Provider/model, seed, temperature, timeout, retry, concurrency, and budget configuration.
- [x] Task-level resume and response cache.
- [x] Raw and normalized output paths retained in run manifest.
- [x] Metric recomputation without provider calls.
- [x] Paired statistics with confidence intervals/effect sizes/Holm correction.
- [x] Mock/non-formal results visibly labeled.
- [x] Secret-scanned anonymous packaging command.
- [ ] Human review completed for 120 benchmark tasks.
- [ ] Formal live-model Core run completed.
- [ ] Actual model release/date and current prices frozen.
- [ ] Cross-application MusicXML checks in MuseScore and Sibelius completed.
- [ ] Official ICMC template and current CFP fields applied.

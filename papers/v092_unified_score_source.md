# V0.92 Unified Score Source

V0.92 makes `ScoreDocument` the canonical post-generation representation. Earlier generated-score preview and playback paths could read simplified `plan.measures`, which meant the first page and audio could disagree with the exported MusicXML or Workbench state.

The V0.92 contract is:

```text
Prompt -> Plan -> Generator -> MusicXML -> ScoreDocument -> Preview / Playback / Export / Workbench
```

The Agent Plan remains inspectable as planning metadata, but rendered score, MIDI fallback events, MusicXML export, and Workbench editing now use `score_document` or outputs derived from the same document. A consistency report compares MusicXML note/rest counts, ScoreDocument events, MIDI note events, measure counts, staff coverage, empty measures, and generated MIDI presence.

Larger symbolic-model training is postponed until this score-source contract is stable, because model quality cannot be evaluated reliably if preview, playback, and exported artifacts disagree.

## V0.93 Correction

V0.93 tightens the V0.92 contract by treating a simplified ScoreDocument SVG as only one explicit source, not as proof of backend engraving. The preferred preview path is backend-rendered SVG/PNG/PDF from real MusicXML; if that is unavailable, Sera may use ScoreDocument rendering or MusicXML text, but it must label the source. `plan.measures` is not allowed in final preview or final playback components.

The consistency report is now complemented by notation grammar validation and fake-rendering regression tests. Event-count agreement remains necessary but insufficient.

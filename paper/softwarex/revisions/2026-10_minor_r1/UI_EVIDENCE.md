# Actual UI evidence 3 October 2026

The screenshots are unmodified captures of the source React interface in the
in-app browser, backed by the real local FastAPI service. Provider set to local in
the test process using a separate unused settings-file path; existing user settings
were not changed. No API requests were made for this evidence. These are not
screenshots of the packaged Electron shell or proof of a live model edit.

1. Import benchmark/source_scores/score_001.musicxml through Import host MusicXML.
   The selected host was MuseScore; the UI labels this as a connected MuseScore
   session even though the import was manual. Captions explicitly disclose this.
2. “Transpose measure 1 staff 1 up two semitones and preserve rhythm; leave staff 2
   unchanged.” produced Unsupported edit, disabled apply, and unchanged score.
   ui_rejection.jpg preserves that failure; ui_rejection_full.jpg repeats the same
   unsupported wording after undo and captures the entire page.
3. The benchmark wording “Transpose measure 1 of staff 1 up by a major second while
   preserving rhythm.” produced a valid proposal: four changed events and no
   reported non-target changes. ui_proposal.jpg is the initial viewport capture;
   ui_proposal_full.jpg repeats the same proposal after undo at revision 2 and
   captures the whole page. No content was fabricated or composited.
4. Apply created revision 1; ui_applied.jpg shows the Undo last agent revision control.
5. Undo created revision 2; ui_undo.jpg records the resulting undo-revision message.
   This is Sera session undo, not a single undo inside MuseScore.

## Separate bridge visual check

MuseScore was launched and its update notice dismissed without installing updates.
The native file-picker automation could not reliably focus its filename control;
no completed plugin send/open-revision sequence was captured. Therefore bridge
visual acceptance remains OPEN. Existing automated host tests and manual import
screenshots do not close that item. Capture the actual Sera Score Bridge panel and
opened reviewed revision before claiming complete bridge visual verification.
The implemented 4.5.2 path uses a saved file and CLI conversion because QML
writeScore/readScore are unavailable; unsaved host changes are excluded.

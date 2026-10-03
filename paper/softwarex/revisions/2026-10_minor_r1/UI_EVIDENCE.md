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

## Actual native bridge verification on 3 October 2026

The earlier native file-picker focus failure was resolved. A separate synthetic
score was opened in MuseScore 4.5.2 and saved as bridge_fixture.mscz. The user's
existing score remained open and was not used as test data.

1. Open benchmark/source_scores/score_001.musicxml and Save As a new local MSCZ.
2. Start Sera Desktop from source (Electron development shell, production frontend
   build), with SERA_LLM_PROVIDER=local and a separate unused SERA_LLM_ENV_FILE.
3. Run Sera Score Bridge 0.3.3; Choose the matching saved MSCZ; click Send. The
   backend manifest records conversion_mode=musescore_cli. Sera automatically
   receives the session. No range was selected: M1 was the default scope. This run
   does not add evidence about transfer of a nonempty host selection.
4. Switch to Edit proposal and enter the exact major-second instruction above.
   Review the four-event transpose, successful validation and protected-scope result.
5. Apply and create host revision; return to the plugin and click Refresh and open
   applied revision. A separate MuseScore window visibly renders revision 1.
6. In Sera click Undo last agent revision. Revision 2 restores the original note
   sequence in the saved XML; it was not separately opened in MuseScore.

Session: bridge_20261003_023845_006da98a. Source implementation: cad7e60.
No live model was called, and this does not validate a packaged installer.

| Native capture | Observed state |
| --- | --- |
| [bridge_source.jpg](figures/bridge_source.jpg) | Original synthetic score in MuseScore |
| [bridge_sent.jpg](figures/bridge_sent.jpg) | Plugin with actual created session |
| [bridge_received.jpg](figures/bridge_received.jpg) | Electron receives the host score |
| [bridge_proposal.jpg](figures/bridge_proposal.jpg) | Valid proposal with four pitch changes |
| [bridge_applied.jpg](figures/bridge_applied.jpg) | Host revision 1 and undo control |
| [bridge_opened.jpg](figures/bridge_opened.jpg) | Plugin reports opening revision 1 |
| [bridge_revision.jpg](figures/bridge_revision.jpg) | Separate MuseScore window renders revision 1 |
| [bridge_undo.jpg](figures/bridge_undo.jpg) | Sera reports undo revision 2 |

All captures are unmodified. The screenshots are accompanied by the original saved
MSCZ, imported MusicXML, revisions 1–2 and session manifest in bridge_evidence/.
BRIDGE_VISUAL_ACCEPTANCE.json records their hashes and independent XML checks.
Exactly four target notes change C4/D4/E4/G4 to D4/E4/F#4/A4. All 16 notes retain
duration, voice and location; the remaining 12 pitches are unchanged; undo restores
all 16 notes. The UI shows operation summaries and element counts, not a graphical
note-diff viewer. Host screenshots and saved XML provide the before/after evidence.

The native bridge visual item is now locally verified for this demonstration.
Single-step host undo, in-place editing, broader host/platform coverage and musical
acceptance remain outside this evidence. Native/compressed files use CLI conversion;
plain MusicXML/XML files are read directly. The user must choose the file matching
the open score and save edits before sending.

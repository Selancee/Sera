# SeraEdit user manual

## Purpose and safety boundary

SeraEdit is an editing agent beside a professional notation host. MuseScore or
another MusicXML-capable application remains the visual notation authority. SeraEdit
does not provide a replacement score editor and does not silently overwrite the
source score. It creates a reviewable revision after validation.

## Minimal offline demonstration

1. Start Sera Desktop or the backend/frontend development pair.
2. Open the Agent view and import a MusicXML file, or use a local demo fixture.
3. Select a narrow scope, preferably one or two measures and a specific staff/voice.
4. Enter an executable instruction, for example:
   `Transpose measures 1-2 of staff 1 up two semitones and preserve rhythm.`
5. Choose **Generate proposal**. With no API key, the supported deterministic path
   still produces locally validated edits for the operation families it recognizes.
6. Inspect the human-readable operations, changed/protected element counts, source
   fingerprint and validation report.
7. Apply only a proposal marked valid. Rejecting leaves the score unchanged.
8. Export/open the reviewed MusicXML revision in the notation host and inspect it.

If the host selection is wider than the location explicitly named in the instruction,
Sera narrows the effective target to that named measure/staff and records the excluded
host area in patch provenance. For example, selecting measures 2-3 while requesting
"the final two notes of measure 2 staff 1" edits measure 2 only. An instruction that
names a measure or staff outside the host selection is rejected instead of broadening
authorization.

## MuseScore bridge workflow

1. Install `integrations/musescore/SeraBridge` as a MuseScore Studio 4 plugin.
2. Start Sera Desktop and wait until its backend health check reports ready.
3. In MuseScore, open a score and select a region when a narrow target is desired.
4. Run **Sera Score Bridge**, then choose **Send score / selection to Sera**.
5. In Sera, request and review a patch. Sera writes a separate reviewed revision.
6. In the bridge, choose **Refresh and open applied revision**. The original open score
   is not overwritten; use MuseScore to compare and save the revision deliberately.

The bridge exchanges a temporary MusicXML snapshot. It is not a claim of direct,
in-place manipulation of MuseScore's internal document model.

## Operation families

The strict research schema includes transpose, exact pitch, duration, insertion,
deletion, dynamics, articulations, ties, slurs, key/time signatures, voice moves,
motif duplication, chord replacement and batch operations. Product/host support is
more conservative: an operation is enabled only when its source-preservation and
round-trip contract is implemented. Unsupported or ambiguous instructions fail
closed instead of being presented as completed edits.

## LLM configuration

In Sera Desktop, open **Model settings**, select an OpenAI-compatible provider,
enter the model and API key, then save. Credentials are stored in the Windows
current-user settings area and are never included in experiment artifacts. The LLM
proposes a high-level plan or patch; server-side validation remains authoritative.

Composer responds in two stages: local candidates arrive first, while optional live
LLM refinement runs in the background. A longer provider timeout does not weaken
the patch validators or automatically apply a candidate.

## Reading validation results

- `valid`: all enabled checks passed; the revision may be reviewed/applied.
- `warning`: no hard invariant failed, but a documented caveat needs attention.
- `invalid`: applying would violate schema, structure, duration, notation relation,
  protected scope, source fingerprint or MusicXML round-trip requirements.
- `unsupported`: the requested operation is outside the implemented contract.

A rejection is an expected safety outcome. Narrow the scope, name the staff/voice,
specify exact pitches/dynamics, or request a supported operation instead of removing
the validator.

## Reviewing the 120-task research benchmark

The ordinary product build does not display the benchmark-review workspace. For a
dedicated source-level research build, set `VITE_SERA_ENABLE_RESEARCH_REVIEW=true`
before building the frontend; **Research review** then appears in the Agent header.
The workspace lists all core tasks and shows instruction/scope/Gold/deterministic diff
evidence, and delegates visual score inspection to the professional MusicXML host.
The **Agent runtime** filter places failed or unverified cases first. For every passed
task, **Open Sera English output** and **Open Sera Chinese output** open the actual
product-replay MusicXML, separately from the Gold expected score. The task badge reports
how many generation/transaction/round-trip runs passed. These local deterministic runs
verify the product path; they are not reported as LLM model performance.
Review decisions are appended outside the repository and do not mutate benchmark
files. See `docs/softwarex/HUMAN_REVIEW_PROTOCOL.md` for the decision rubric, 30-task
secondary-review sample and the evidence threshold for later aesthetic calibration.
The completed publication snapshot is under
`experiments/softwarex_human_review_120_v1`; normal users do not need this interface.

## Reset and recovery

Rejecting a preview does not mutate the canonical score. Accepted transactions keep
before/after snapshots for undo/redo. Host revisions are separate files; the source
MusicXML is retained unless the user explicitly replaces it in the notation host.

## Known limitations

- Structural orchestration, new instruments/parts and unrestricted composition are
  not guaranteed by the host-safe path.
- Complex tuplets, grace relations and unusual multi-voice notation require careful
  host review even after internal validation.
- The symbolic playability and melodic-expectation values are engineering proxies,
  not aesthetic judgments.
- MuseScore bridge behavior has been exercised; Sibelius round-trip integration is
  not claimed as verified.

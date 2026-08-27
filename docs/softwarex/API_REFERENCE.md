# SeraEdit API and developer reference

The running FastAPI application publishes the exact OpenAPI contract at `/openapi.json`
and interactive documentation at `/docs`. This document identifies stable research
concepts and discovery routes; endpoint payload schemas remain authoritative in OpenAPI.

## Core data contracts

### ScoreDocument

The canonical score dictionary contains score metadata, measures, staff/voice tracks
and stable event identifiers. Exact patch validation computes a canonical SHA-256
fingerprint before and after a transaction. Callers must not mutate a ScoreDocument
that has been passed into the transaction layer.

### ScoreScope

`sera_edit.domain.score_scope.ScoreScope` selects measures, parts, staffs, voices,
event IDs and optional time ranges. A target scope is the allowed editing region;
protected scope and explicit exclusions are immutable unless a separate user-confirmed
workflow is used. Formal evaluation disables protected-scope override.

Interactive generation additionally resolves an explicit measure/staff named in the
instruction against the host-owned target. `instruction_scope.py` may narrow the host
selection, but never expands it. The effective scope, requested scope and excluded host
measures/staffs are stored in patch provenance. A named location outside the host
selection returns `unsupported` before provider planning or transaction execution.

### ScorePatch

`sera_edit.domain.score_patch.ScorePatch` binds an instruction and operation list to
a source score ID/fingerprint, target scope, protected scope, preconditions, expected
effects and provider provenance. The JSON Schema is
`benchmark/schemas/score_patch.schema.json`.

### ValidationReport

Every validator returns a normalized status (`valid`, `warning`, `invalid`, or
`unsupported`) plus errors, warnings, check evidence, repairability and bounded repair
suggestions. Transaction failure never commits a partial score.

## Research endpoints

Routes are mounted from `sera_edit/api/routes.py`. Query `/openapi.json` in the tested
version to confirm exact paths and payloads. Principal route families include:

- host session creation/import and reviewed-revision export;
- non-mutating host-session reactivation at
  `POST /integrations/notation-sessions/{session_id}/activate`, used only to restore
  desktop focus after a missed notification or backend restart;
- patch generation, preview, validation, apply/reject and revert;
- Composer preview and asynchronous LLM-refinement polling;
- provider settings/status without returning stored secret values;
- benchmark/demo fixture loading;
- local benchmark review at `/sera-edit/review/summary`, `/review/tasks`,
  `/review/decisions`, `/review/tasks/{task_id}/artifacts/{variant}`, and
  `/review/export` (all paths below the `/sera-edit` prefix).

Review writes are append-only and remain outside the repository by default. The task
detail response contains compact score metadata, Gold operations, deterministic event
diffs, automatic-validation evidence and a content fingerprint; it does not send a
notation canvas or provide manual score editing.

## Transaction lifecycle

```text
source fingerprint -> schema -> selectors/preconditions -> clone -> apply operations
-> structure/duration/notation validation -> protected-scope diff -> MusicXML round trip
-> commit or rollback -> undo history
```

Use `PatchTransaction.preview()` for dry runs. Consumers should display the returned
diff and report before requesting a commit. Any source-fingerprint mismatch means the
host score changed after proposal generation and the proposal must be regenerated.

## Provider extension

Implement the common interface in `sera_edit/providers/base.py`. A provider response
must preserve raw text, parsed output, provider/model, latency, token counts, estimated
cost, request ID, finish reason and normalized error. Keys are read only from runtime
settings/environment and must never be serialized into response metadata.

## Evaluation extension

Conditions in `evaluation/conditions` must remain separated:

- `full_rewrite`: full MusicXML returned without Sera-specific patch repair;
- `patch_only`: schema parsing and basic application only;
- `sera_full`: complete source-bound transaction, validation, repair/refusal and
  round-trip pipeline.

New metrics must be deterministic whenever they can be computed from source/output.
Raw responses must remain available so metrics can be recomputed without another API
call.

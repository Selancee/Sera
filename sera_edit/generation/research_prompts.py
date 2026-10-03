"""Answer-blind protocol for new live comparisons; legacy prompts stay frozen."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from backend.services.score_document_service import score_document_to_musicxml
from sera_edit.generation.prompts import compact_score_context, sera_response_schema


PATCH_PROMPT = (
    'Return only a ScorePatch 1.0.0 JSON object using the supplied schema and event IDs. '
    'Copy the source identity, fingerprint, target_scope and protected_scope exactly. '
    'Implement the instruction while preserving unspecified content. '
    'For conflicting or unsupported instructions return {"refusal":true,"reason":"..."}. '
    'Do not return prose or Markdown.'
)
PROMPTS = {
    "full_rewrite": 'Edit the supplied MusicXML according to the instruction and scopes. '
    'Preserve unspecified content. Return only the complete modified MusicXML. '
    'For conflicting or unsupported instructions return {"refusal":true,"reason":"..."}.',
    "patch_only": PATCH_PROMPT,
    "sera_full": PATCH_PROMPT,
    "sera_repair": PATCH_PROMPT + ' Repair the supplied candidate using the validation errors.',
}

# Public operation API, independent of benchmark targets and Gold patches.
OPERATION_ARGUMENTS = {
    "transpose": {"semitones": "integer"}, "set_pitch": {"pitch": "C4-style pitch"},
    "set_duration": {"duration": "whole/half/quarter/eighth/16th, optionally dotted"},
    "set_dynamic": {"dynamic": "ppp/pp/p/mp/mf/f/ff/fff"},
    "set_articulation": {"articulations": "list of notation names"},
    "set_tie": {"tie": "start/stop/continue or null"},
    "set_slur": {"slur": "start/stop/continue or null"},
    "move_to_voice": {"voice": "positive integer"}, "delete_event": {},
    "insert_note": {"pitch": "pitch", "duration": "duration name", "offset": "quarter-note units", "staff": "1 or 2", "voice": "integer", "event_id": "new unique ID"},
    "insert_rest": {"duration": "duration name", "offset": "quarter-note units", "staff": "1 or 2", "voice": "integer", "event_id": "new unique ID"},
    "change_key_signature": {"key": "key name; requires whole_score target"},
    "change_time_signature": {"meter": "numerator/denominator; requires whole_score target"},
    "duplicate_motif": {"target_measure": "integer", "offset_delta": "quarter-note units"},
    "replace_chord": {"pitches": "list of pitches"}, "batch": {"operations": "list of operation objects"},
}


def metadata(condition: str) -> dict[str, str]:
    prompt = PROMPTS[condition]
    return {"prompt_version": f"{condition}_answer_blind_v2.0", "prompt": prompt,
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()}


def messages(condition: str, task: dict, score: dict, *, repair: dict | None = None) -> tuple[list[dict[str, str]], Any]:
    # Deliberate allowlist: no task identifiers, labels, expected outputs, Gold
    # patches, scoring constraints, or unsupported_reason enter model input.
    payload = {"instruction": task["instruction_en"], "target_scope": task["target_scope"],
               "protected_scope": task["protected_scope"]}
    schema = None
    if condition == "full_rewrite":
        payload["original_musicxml"] = score_document_to_musicxml(score)
    else:
        payload["score_context"] = compact_score_context(score, task["target_scope"])
        schema = sera_response_schema()
        payload["response_schema"] = schema
        payload["operation_arguments"] = OPERATION_ARGUMENTS
        payload["supported_checked_effects"] = {
            "preserve_pitch": {}, "preserve_duration": {},
            "changed_element_count": {"value": "integer"},
            "dynamic_equals": {"event_id": "existing ID", "value": "dynamic name"},
        }
    if repair is not None:
        payload.update(repair)
    return [{"role": "system", "content": PROMPTS[condition]},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}], schema

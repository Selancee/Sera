"""Public JSON contract clarification after the retained v2 live smoke pilot."""
from __future__ import annotations

import hashlib
import json

from sera_edit.generation import research_prompts as v2


CONTRACT = {
    "preconditions": {
        "format": "An array of objects with a type field; use [] when no additional precondition is needed.",
        "supported_forms": [
            {"type": "event_exists", "event_id": "<existing event ID>"},
            {"type": "minimum_event_count", "value": "<integer>"},
        ],
        "operation_preconditions": "Use [] (operation-level semantic assertions are not implemented).",
    },
    "expected_effects": {
        "format": "An array of objects with a type field. Do not use the type name as an object key. Use [] if none is needed.",
        "supported_forms": [
            {"type": "preserve_pitch"}, {"type": "preserve_duration"},
            {"type": "changed_element_count", "value": "<integer>"},
            {"type": "dynamic_equals", "event_id": "<existing event ID>", "value": "<dynamic name>"},
        ],
    },
    "operation_expected_change_count": (
        "Optional: omit or set null unless the exact number of affected event IDs is known. "
        "This counts event IDs, not global attributes; change_key_signature and change_time_signature count zero event IDs."
    ),
    "selectors": "set_pitch/set_duration/set_dynamic/set_articulation/set_tie/set_slur/move_to_voice/delete_event require event_ids. insert_note/insert_rest require measures.",
}


def _prompt(condition: str) -> str:
    suffix = " Follow the public condition_contract for preconditions and expected_effects; do not invent assertion formats."
    return v2.PROMPTS[condition] + (suffix if condition != "full_rewrite" else "")


def metadata(condition: str) -> dict[str, str]:
    prompt = _prompt(condition)
    return {"prompt_version": f"{condition}_answer_blind_v3.0", "prompt": prompt,
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()}


def messages(condition: str, task: dict, score: dict, *, repair: dict | None = None):
    result, schema = v2.messages(condition, task, score, repair=repair)
    result[0]["content"] = _prompt(condition)
    if condition != "full_rewrite":
        payload = json.loads(result[1]["content"])
        payload.pop("supported_checked_effects", None)
        payload["condition_contract"] = CONTRACT
        result[1]["content"] = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return result, schema

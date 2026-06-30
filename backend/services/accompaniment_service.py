"""Simple fallback-safe accompaniment generation for Workbench V0.8."""

from __future__ import annotations

import uuid
from typing import Any


ROOTS = {
    "I": "C3",
    "i": "C3",
    "ii": "D3",
    "IV": "F3",
    "V": "G2",
    "vi": "A2",
}


def generate_left_hand_accompaniment_patch(
    score_document: dict[str, Any],
    selected_range: dict[str, Any],
    texture: str = "arpeggiated",
) -> dict[str, Any]:
    """Create a local ScorePatch with simple left-hand accompaniment notes."""

    start = int(selected_range.get("start_measure", 1))
    end = int(selected_range.get("end_measure", start))
    operations: list[dict[str, Any]] = []
    for measure in score_document.get("measures", []):
        number = int(measure.get("number", 0))
        if not start <= number <= end:
            continue
        root = ROOTS.get(str(measure.get("harmony", "I")), "C3")
        pitches = _texture_pitches(root, texture)
        offsets = [0, 0, 0] if texture == "block_chord" else [0, 1, 1] if texture == "bass_chord" else [0, 0.5, 1, 1.5]
        for index, pitch in enumerate(pitches):
            operations.append(
                {
                    "source": "agent",
                    "type": "insert_note",
                    "target": {"measure_id": measure.get("measure_id"), "measure": number, "staff": "left_hand", "voice": 1},
                    "after": {
                        "event_id": f"{measure.get('measure_id', 'm')}_lh_{texture}_{index}",
                        "pitch": pitch,
                        "duration": "half" if texture == "block_chord" else "eighth",
                        "offset": offsets[index] if index < len(offsets) else index * 0.5,
                        "staff": "left_hand",
                        "voice": 1,
                        "dynamic": "mp",
                    },
                    "description": f"Generate {texture} left-hand accompaniment.",
                }
            )
    return {
        "patch_id": f"patch_lh_{uuid.uuid4().hex[:10]}",
        "patch_type": "update_texture",
        "target_range": {"start_measure": start, "end_measure": end},
        "operations": operations,
        "rationale": "Generate a simple left-hand accompaniment from measure harmony labels.",
        "expected_effect": "Adds a playable bass/accompaniment layer while preserving the right hand.",
        "prompt_alignment": {
            "instruction": "Generate left-hand accompaniment",
            "matched_aspects": ["left hand", "accompaniment", "selected range"],
            "risk_aspects": ["harmony labels are heuristic"],
        },
        "validation_expectations": {
            "should_preserve_measure_count": True,
            "should_preserve_meter": True,
            "should_preserve_harmony": True,
        },
    }


def _texture_pitches(root: str, texture: str) -> list[str]:
    third = root.replace("C", "E", 1).replace("D", "F", 1).replace("F", "A", 1).replace("G", "B", 1).replace("A", "C", 1)
    fifth = root.replace("C", "G", 1).replace("D", "A", 1).replace("F", "C", 1).replace("G", "D", 1).replace("A", "E", 1)
    if texture == "arpeggiated":
        return [root, fifth, third, fifth]
    return [root, third, fifth]

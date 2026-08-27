"""Source-preserving MusicXML patches for notation-host revisions.

The notation bridge must not rebuild an imported host score from Sera's
reduced canonical model for bounded edits.  Rebuilding loses layout/defaults
and can materialize inherited dynamics or implicit rests.  This module changes
only explicitly supported XML nodes in the original MusicXML document.
"""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from backend.notation.duration_math import DURATION_TO_FRACTION
from backend.services.musicxml_voice_service import (
    local_voice_from_musicxml,
    musicxml_voice_for_staff,
)
from sera_edit.domain.score_scope import iter_event_contexts
from sera_edit.execution.diff_engine import score_diff


class SourcePreservingPatchError(ValueError):
    """Raised when an edit cannot be represented without rebuilding the score."""


@dataclass(frozen=True, slots=True)
class _NoteNode:
    event_id: str
    measure: int
    staff: str
    voice: int
    note: ET.Element
    measure_node: ET.Element
    divisions: int


_SUPPORTED_EVENT_FIELDS = {
    "pitch",
    "duration",
    "voice",
    "tie",
    "slur",
    "dynamic",
    "articulations",
    "beam",
}
_SUPPORTED_GLOBAL_FIELDS = {"key", "meter"}
_PITCH_RE = re.compile(r"^([A-Ga-g])([#b]*)(-?\d+)$")
_MAJOR_KEY_FIFTHS = {
    "Cb": -7,
    "Gb": -6,
    "Db": -5,
    "Ab": -4,
    "Eb": -3,
    "Bb": -2,
    "F": -1,
    "C": 0,
    "G": 1,
    "D": 2,
    "A": 3,
    "E": 4,
    "B": 5,
    "F#": 6,
    "C#": 7,
}
_MINOR_KEY_FIFTHS = {
    "Ab": -7,
    "Eb": -6,
    "Bb": -5,
    "F": -4,
    "C": -3,
    "G": -2,
    "D": -1,
    "A": 0,
    "E": 1,
    "B": 2,
    "F#": 3,
    "C#": 4,
    "G#": 5,
    "D#": 6,
    "A#": 7,
}


def patch_musicxml_preserving_source(
    source_musicxml: str,
    before_score: dict[str, Any],
    after_score: dict[str, Any],
) -> dict[str, Any]:
    """Patch supported fields in source MusicXML while preserving all other XML."""

    source_text = str(source_musicxml or "")
    try:
        root = ET.fromstring(source_text)
    except ET.ParseError as exc:
        raise SourcePreservingPatchError(f"Source MusicXML is not well formed: {exc}") from exc

    diff = score_diff(before_score, after_score)
    unsupported_global_fields = sorted(set(diff["global_changes"]) - _SUPPORTED_GLOBAL_FIELDS)
    if unsupported_global_fields:
        fields = ", ".join(unsupported_global_fields)
        raise SourcePreservingPatchError(
            f"Source-preserving host export does not yet support global changes: {fields}."
        )

    unsupported: dict[str, list[str]] = {}
    for item in diff["changed"]:
        fields = sorted(set(item["changed_fields"]) - _SUPPORTED_EVENT_FIELDS)
        if fields:
            unsupported[item["event_id"]] = fields
    if unsupported:
        summary = "; ".join(f"{event_id}: {','.join(fields)}" for event_id, fields in sorted(unsupported.items()))
        raise SourcePreservingPatchError(
            "Refusing to rebuild the full host score for unsupported event fields: " + summary
        )

    node_index = _note_node_index(root)
    before_index = {context.event_id: context for context in iter_event_contexts(before_score)}
    after_index = {context.event_id: context for context in iter_event_contexts(after_score)}
    changed_ids = [item["event_id"] for item in diff["changed"]]
    missing = sorted(event_id for event_id in changed_ids if event_id not in node_index or event_id not in after_index)
    if missing:
        raise SourcePreservingPatchError(
            "Could not map changed event IDs back to the source MusicXML: " + ", ".join(missing)
        )

    added_ids = [item["event_id"] for item in diff["added"]]
    deleted_ids = [item["event_id"] for item in diff["deleted"]]
    if added_ids or deleted_ids:
        _persist_existing_event_ids(node_index, before_index)
        _apply_structural_replacements(
            node_index=node_index,
            before_index=before_index,
            after_index=after_index,
            added_ids=added_ids,
            deleted_ids=deleted_ids,
        )

    changed_global_fields = sorted(diff["global_changes"])
    if "key" in changed_global_fields:
        _set_initial_key_signature(root, str((after_score.get("global") or {}).get("key", "")))
    if "meter" in changed_global_fields:
        before_meter = str((before_score.get("global") or {}).get("meter", ""))
        after_meter = str((after_score.get("global") or {}).get("meter", ""))
        _set_initial_time_signature(root, before_meter, after_meter)

    voice_changed = any("voice" in item["changed_fields"] for item in diff["changed"])
    normalized_host_voice_count = _normalize_staff_local_voice_tokens(root) if voice_changed else 0

    dynamic_changed_ids: set[str] = set()
    for item in diff["changed"]:
        event_id = item["event_id"]
        fields = set(item["changed_fields"])
        node = node_index[event_id]
        event = after_index[event_id].event
        if "pitch" in fields:
            _set_pitch(node.note, str(event.get("pitch", "")))
        if "duration" in fields:
            _set_duration(node.note, str(event.get("duration", "")), node.divisions)
        if "voice" in fields:
            _set_voice(node.note, int(event.get("voice", 1) or 1), node.staff)
        if "tie" in fields:
            _set_tie(node.note, event.get("tie"))
        if "slur" in fields:
            _set_slur(node.note, event.get("slur"))
        if "beam" in fields:
            _set_beam(node.note, event.get("beam"))
        if "articulations" in fields:
            _set_articulations(node.note, list(event.get("articulations") or []))
        if "dynamic" in fields:
            dynamic_changed_ids.add(event_id)

    for event_id, dynamic in _dynamic_boundary_marks(after_index, dynamic_changed_ids):
        if event_id not in node_index:
            raise SourcePreservingPatchError(
                f"Could not map dynamic boundary event back to source MusicXML: {event_id}"
            )
        _set_note_dynamic(node_index[event_id].note, dynamic)

    _set_title_and_composer(root, before_score, after_score)
    changed_top_level = [
        field
        for field in ("title", "composer")
        if str(before_score.get(field, "")) != str(after_score.get(field, ""))
    ]
    if not diff["changed"] and not added_ids and not deleted_ids and not changed_top_level and not changed_global_fields:
        musicxml = source_text
        export_mode = "source_preserving_noop"
    else:
        musicxml = _serialize_with_original_prolog(source_text, root)
        if added_ids or deleted_ids:
            export_mode = "source_preserving_structural_patch"
        elif changed_global_fields:
            export_mode = "source_preserving_global_patch"
        else:
            export_mode = "source_preserving_patch"
    all_changed_ids = [*changed_ids, *added_ids, *deleted_ids]
    changed_fields = sorted({field for item in diff["changed"] for field in item["changed_fields"]})
    if added_ids:
        changed_fields.append("event_inserted")
    if deleted_ids:
        changed_fields.append("event_deleted")
    changed_fields.extend(changed_global_fields)
    return {
        "musicxml": musicxml,
        "export_mode": export_mode,
        "changed_event_count": len(all_changed_ids),
        "changed_event_ids": all_changed_ids,
        "added_event_ids": added_ids,
        "deleted_event_ids": deleted_ids,
        "changed_fields": sorted(set(changed_fields)),
        "changed_top_level_fields": changed_top_level,
        "changed_global_fields": changed_global_fields,
        "normalized_host_voice_count": normalized_host_voice_count,
    }


def _apply_structural_replacements(
    *,
    node_index: dict[str, _NoteNode],
    before_index: dict[str, Any],
    after_index: dict[str, Any],
    added_ids: list[str],
    deleted_ids: list[str],
) -> None:
    """Apply deletions and same-onset replacements without rebuilding a score.

    The benchmark's insertion/deletion edits are duration-preserving
    replacements: one existing note is exchanged for another note or chord at
    the same measure, staff, voice, and offset.  Cloning the original MusicXML
    note keeps layout, beams, tuplets, and all non-target XML intact while the
    event identity and pitch are updated explicitly.  Pure deletions are also
    safe because they remove only the mapped ``note`` element; arbitrary
    insertion without an existing same-onset template remains unsupported.
    """

    missing_deleted = sorted(event_id for event_id in deleted_ids if event_id not in node_index or event_id not in before_index)
    missing_added = sorted(event_id for event_id in added_ids if event_id not in after_index)
    if missing_deleted or missing_added:
        missing = [*missing_deleted, *missing_added]
        raise SourcePreservingPatchError(
            "Could not map structural event IDs for source-preserving export: " + ", ".join(missing)
        )

    deleted_groups = _group_event_ids(before_index, deleted_ids)
    added_groups = _group_event_ids(after_index, added_ids)
    unmatched_insertions = sorted(set(added_groups) - set(deleted_groups))
    if unmatched_insertions:
        raise SourcePreservingPatchError(
            "Source-preserving structural export only supports insertion when replacing an event at the same measure, staff, voice, and offset."
        )

    for key in sorted(deleted_groups):
        old_ids = deleted_groups[key]
        new_ids = added_groups.get(key, [])
        if not new_ids:
            _remove_event_nodes(node_index, before_index, after_index, old_ids)
            continue
        old_events = [before_index[event_id].event for event_id in old_ids]
        new_events = [after_index[event_id].event for event_id in new_ids]
        old_durations = {str(event.get("duration", "quarter")) for event in old_events if not event.get("grace")}
        new_durations = {str(event.get("duration", "quarter")) for event in new_events if not event.get("grace")}
        if old_durations != new_durations or len(old_durations) > 1:
            raise SourcePreservingPatchError(
                "Source-preserving structural export requires replacement events to keep the original duration."
            )
        if any(event.get("type") == "rest" for event in [*old_events, *new_events]):
            raise SourcePreservingPatchError(
                "Source-preserving structural export does not yet support replacing rests."
            )

        old_nodes = [node_index[event_id] for event_id in old_ids]
        measure_nodes = {id(node.measure_node): node.measure_node for node in old_nodes}
        if len(measure_nodes) != 1:
            raise SourcePreservingPatchError("Structural replacement events must belong to one MusicXML measure.")
        measure_node = next(iter(measure_nodes.values()))
        positions = [list(measure_node).index(node.note) for node in old_nodes]
        insertion_position = min(positions)
        template = min(old_nodes, key=lambda node: list(measure_node).index(node.note)).note
        for node in sorted(old_nodes, key=lambda item: list(measure_node).index(item.note), reverse=True):
            measure_node.remove(node.note)

        ordered_new_ids = sorted(
            new_ids,
            key=lambda event_id: (
                bool(after_index[event_id].event.get("is_chord_tone")),
                event_id,
            ),
        )
        for position, event_id in enumerate(ordered_new_ids):
            event = after_index[event_id].event
            note = copy.deepcopy(template)
            _set_pitch(note, str(event.get("pitch", "")))
            _set_event_id(note, event_id, event.get("chord_group_id"))
            _set_chord_marker(note, position > 0)
            _set_beam(note, event.get("beam"))
            _set_articulations(note, list(event.get("articulations") or []))
            if position > 0:
                _remove_note_dynamics(note)
            measure_node.insert(insertion_position + position, note)


def _persist_existing_event_ids(node_index: dict[str, _NoteNode], before_index: dict[str, Any]) -> None:
    """Persist generated IDs before a structural edit can shift note ordering."""

    for event_id, node in node_index.items():
        if _technical_event_id(node.note) is not None:
            continue
        context = before_index.get(event_id)
        chord_group_id = context.event.get("chord_group_id") if context is not None else None
        _set_event_id(node.note, event_id, chord_group_id)


def _remove_event_nodes(
    node_index: dict[str, _NoteNode],
    before_index: dict[str, Any],
    after_index: dict[str, Any],
    event_ids: list[str],
) -> None:
    """Remove mapped notes and keep a surviving chord anchor well formed."""

    nodes = [node_index[event_id] for event_id in event_ids]
    measures = {id(node.measure_node): node.measure_node for node in nodes}
    if len(measures) != 1:
        raise SourcePreservingPatchError("Deleted events must belong to one MusicXML measure group.")
    measure_node = next(iter(measures.values()))
    positions = sorted(list(measure_node).index(node.note) for node in nodes)
    first_position = positions[0]
    for node in sorted(nodes, key=lambda item: list(measure_node).index(item.note), reverse=True):
        measure_node.remove(node.note)

    # If the root note of a chord was removed but one of its chord tones
    # survives, that first survivor becomes the new rhythmic anchor.
    children = list(measure_node)
    if first_position >= len(children):
        return
    candidate = children[first_position]
    if _local_name(candidate.tag) != "note" or _child(candidate, "chord") is None:
        return
    candidate_id = _technical_event_id(candidate)
    if not candidate_id or candidate_id not in before_index or candidate_id not in after_index:
        return
    old_context = before_index[candidate_id]
    deleted_context = before_index[event_ids[0]]
    if (
        old_context.measure,
        old_context.staff,
        old_context.voice,
        old_context.offset,
    ) == (
        deleted_context.measure,
        deleted_context.staff,
        deleted_context.voice,
        deleted_context.offset,
    ):
        _set_chord_marker(candidate, False)


def _group_event_ids(index: dict[str, Any], event_ids: list[str]) -> dict[tuple[int, str, int, str], list[str]]:
    groups: dict[tuple[int, str, int, str], list[str]] = {}
    for event_id in event_ids:
        context = index[event_id]
        key = (context.measure, context.staff, context.voice, str(context.offset))
        groups.setdefault(key, []).append(event_id)
    return groups


def _set_event_id(note: ET.Element, event_id: str, chord_group_id: object) -> None:
    notations = _child(note, "notations")
    if notations is None:
        notations = ET.SubElement(note, _qualified_name(note, "notations"))
    technical = _child(notations, "technical")
    if technical is None:
        technical = ET.SubElement(notations, _qualified_name(notations, "technical"))
    for child in list(technical):
        if _local_name(child.tag) != "other-technical":
            continue
        value = (child.text or "").strip()
        if value.startswith("sera-event-id:") or value.startswith("sera-chord-group-id:"):
            technical.remove(child)
    identity = ET.SubElement(technical, _qualified_name(technical, "other-technical"))
    identity.text = f"sera-event-id:{event_id}"
    if chord_group_id:
        chord_group = ET.SubElement(technical, _qualified_name(technical, "other-technical"))
        chord_group.text = f"sera-chord-group-id:{chord_group_id}"


def _set_chord_marker(note: ET.Element, is_chord_tone: bool) -> None:
    chord = _child(note, "chord")
    if is_chord_tone and chord is None:
        chord = ET.Element(_qualified_name(note, "chord"))
        children = list(note)
        insert_at = 1 if children and _local_name(children[0].tag) == "grace" else 0
        note.insert(insert_at, chord)
    elif not is_chord_tone and chord is not None:
        note.remove(chord)


def _set_beam(note: ET.Element, value: object) -> None:
    for child in list(note):
        if _local_name(child.tag) == "beam":
            note.remove(child)
    if not isinstance(value, dict) or not value:
        return
    beam = ET.Element(
        _qualified_name(note, "beam"),
        {"number": str(int(value.get("number", 1) or 1))},
    )
    beam.text = str(value.get("value", "continue"))
    notations = _child(note, "notations")
    if notations is None:
        note.append(beam)
    else:
        note.insert(list(note).index(notations), beam)


def _set_duration(note: ET.Element, value: str, divisions: int) -> None:
    """Write one exact canonical duration without disturbing other notation."""

    if _child(note, "grace") is not None:
        raise SourcePreservingPatchError("Source-preserving duration edits do not target grace notes.")
    normalized = str(value or "").strip().replace("-", "_").replace(" ", "_")
    duration = DURATION_TO_FRACTION.get(normalized)
    notation = {
        Fraction(4, 1): ("whole", False, False),
        Fraction(3, 1): ("half", True, False),
        Fraction(2, 1): ("half", False, False),
        Fraction(3, 2): ("quarter", True, False),
        Fraction(1, 1): ("quarter", False, False),
        Fraction(3, 4): ("eighth", True, False),
        Fraction(1, 2): ("eighth", False, False),
        Fraction(1, 3): ("eighth", False, True),
        Fraction(1, 4): ("16th", False, False),
    }
    if duration is None or duration not in notation:
        raise SourcePreservingPatchError(f"Unsupported source-preserving duration: {value}")
    ticks = duration * max(1, divisions)
    if ticks.denominator != 1:
        raise SourcePreservingPatchError(
            f"Duration {value} cannot be represented exactly with MusicXML divisions={divisions}."
        )
    duration_node = _child(note, "duration")
    if duration_node is None:
        raise SourcePreservingPatchError("The source MusicXML note has no duration element.")
    duration_node.text = str(ticks.numerator)

    note_type, dotted, triplet = notation[duration]
    type_node = _child(note, "type")
    if type_node is None:
        type_node = ET.Element(_qualified_name(note, "type"))
        _insert_before_first(note, type_node, {"dot", "accidental", "time-modification", "staff", "beam", "notations"})
    type_node.text = note_type
    for child in list(note):
        if _local_name(child.tag) in {"dot", "time-modification"}:
            note.remove(child)
    if dotted:
        dot = ET.Element(_qualified_name(note, "dot"))
        note.insert(list(note).index(type_node) + 1, dot)
    if triplet:
        time_modification = ET.Element(_qualified_name(note, "time-modification"))
        actual = ET.SubElement(time_modification, _qualified_name(time_modification, "actual-notes"))
        actual.text = "3"
        normal = ET.SubElement(time_modification, _qualified_name(time_modification, "normal-notes"))
        normal.text = "2"
        normal_type = ET.SubElement(time_modification, _qualified_name(time_modification, "normal-type"))
        normal_type.text = "eighth"
        _insert_before_first(note, time_modification, {"stem", "notehead", "staff", "beam", "notations"})


def _set_voice(note: ET.Element, value: int, staff: str) -> None:
    staff_number = 2 if staff == "left_hand" else 1
    try:
        musicxml_voice = musicxml_voice_for_staff(value, staff_number)
    except ValueError as exc:
        raise SourcePreservingPatchError(str(exc)) from exc
    voice = _child(note, "voice")
    if voice is None:
        voice = ET.Element(_qualified_name(note, "voice"))
        _insert_before_first(note, voice, {"type", "dot", "accidental", "time-modification", "staff", "beam", "notations"})
    voice.text = str(musicxml_voice)


def _normalize_staff_local_voice_tokens(root: ET.Element) -> int:
    """Upgrade legacy staff-local voice tokens before a host voice edit.

    Older Sera exports wrote voice 1/2 independently on both piano staves.
    MusicXML defines a voice at part scope, so MuseScore can interpret those
    duplicate tokens as cross-staff voices and remap unrelated measures. When
    a part has no host-style voice number on a lower staff, convert its lower
    staff tokens to MuseScore's part-wide 5..8 range. Existing MuseScore files
    are already in that form and remain untouched.
    """

    changed = 0
    for part in [node for node in list(root) if _local_name(node.tag) == "part"]:
        notes: list[tuple[ET.Element, int, int]] = []
        for measure in [node for node in list(part) if _local_name(node.tag) == "measure"]:
            for note in [node for node in list(measure) if _local_name(node.tag) == "note"]:
                staff_text = _child_text(note, "staff") or "1"
                voice_text = _child_text(note, "voice") or "1"
                if not staff_text.isdigit() or not voice_text.isdigit():
                    continue
                notes.append((note, max(1, int(staff_text)), max(1, int(voice_text))))
        if not any(staff > 1 for _, staff, _ in notes):
            continue
        if any(staff > 1 and voice > 4 for _, staff, voice in notes):
            continue
        for note, staff, local_voice in notes:
            if staff == 1:
                continue
            try:
                encoded = musicxml_voice_for_staff(local_voice, staff)
            except ValueError as exc:
                raise SourcePreservingPatchError(str(exc)) from exc
            voice_node = _child(note, "voice")
            if voice_node is None:
                voice_node = ET.Element(_qualified_name(note, "voice"))
                _insert_before_first(
                    note,
                    voice_node,
                    {"type", "dot", "accidental", "time-modification", "staff", "beam", "notations"},
                )
            if (voice_node.text or "").strip() != str(encoded):
                voice_node.text = str(encoded)
                changed += 1
    return changed


def _relation_types(value: object) -> list[str]:
    if value == "continue":
        return ["stop", "start"]
    if value in {"start", "stop"}:
        return [str(value)]
    if value in {None, "", False}:
        return []
    raise SourcePreservingPatchError(f"Unsupported MusicXML relation value: {value}")


def _set_tie(note: ET.Element, value: object) -> None:
    relation_types = _relation_types(value)
    for child in list(note):
        if _local_name(child.tag) == "tie":
            note.remove(child)
    insertion_anchor = {"voice", "type", "dot", "accidental", "time-modification", "staff", "beam", "notations"}
    for relation_type in relation_types:
        tie = ET.Element(_qualified_name(note, "tie"), {"type": relation_type})
        _insert_before_first(note, tie, insertion_anchor)
    _set_notation_relation(note, "tied", relation_types)


def _set_slur(note: ET.Element, value: object) -> None:
    _set_notation_relation(note, "slur", _relation_types(value))


def _set_notation_relation(note: ET.Element, name: str, relation_types: list[str]) -> None:
    notations = _child(note, "notations")
    if notations is None and relation_types:
        notations = ET.SubElement(note, _qualified_name(note, "notations"))
    if notations is None:
        return
    for child in list(notations):
        if _local_name(child.tag) == name:
            notations.remove(child)
    for relation_type in relation_types:
        relation = ET.Element(
            _qualified_name(notations, name),
            {"type": relation_type, **({"number": "1"} if name == "slur" else {})},
        )
        insert_at = 0
        if name == "slur":
            while insert_at < len(notations) and _local_name(notations[insert_at].tag) == "tied":
                insert_at += 1
        notations.insert(insert_at, relation)
    if not list(notations):
        note.remove(notations)


def _insert_before_first(parent: ET.Element, node: ET.Element, following_names: set[str]) -> None:
    for index, child in enumerate(list(parent)):
        if _local_name(child.tag) in following_names:
            parent.insert(index, node)
            return
    parent.append(node)


def _remove_note_dynamics(note: ET.Element) -> None:
    notations = _child(note, "notations")
    if notations is None:
        return
    dynamics = _child(notations, "dynamics")
    if dynamics is not None:
        notations.remove(dynamics)


def _set_initial_key_signature(root: ET.Element, key_value: str) -> None:
    """Set each part's initial traditional key without touching later modulations."""

    fifths, mode = _parse_key_signature(key_value)
    parts = [node for node in list(root) if _local_name(node.tag) == "part"]
    if not parts:
        raise SourcePreservingPatchError("Source MusicXML does not contain a score part for the key-signature edit.")

    for part in parts:
        measures = [node for node in list(part) if _local_name(node.tag) == "measure"]
        if not measures:
            raise SourcePreservingPatchError("A source MusicXML part has no measure for the key-signature edit.")
        first_measure = measures[0]
        attributes_nodes: list[ET.Element] = []
        for child in list(first_measure):
            child_name = _local_name(child.tag)
            if child_name in {"note", "backup", "forward"}:
                break
            if child_name == "attributes":
                attributes_nodes.append(child)
        if not attributes_nodes:
            attributes = ET.Element(_qualified_name(first_measure, "attributes"))
            insert_at = 0
            while insert_at < len(first_measure) and _local_name(first_measure[insert_at].tag) == "print":
                insert_at += 1
            first_measure.insert(insert_at, attributes)
            attributes_nodes = [attributes]

        key_nodes = [
            child
            for attributes in attributes_nodes
            for child in list(attributes)
            if _local_name(child.tag) == "key"
        ]
        if not key_nodes:
            attributes = attributes_nodes[0]
            key_node = ET.Element(_qualified_name(attributes, "key"))
            insert_at = 0
            while insert_at < len(attributes) and _local_name(attributes[insert_at].tag) == "divisions":
                insert_at += 1
            attributes.insert(insert_at, key_node)
            key_nodes = [key_node]

        for key_node in key_nodes:
            for child in list(key_node):
                if _local_name(child.tag) in {
                    "cancel",
                    "fifths",
                    "mode",
                    "key-step",
                    "key-alter",
                    "key-accidental",
                }:
                    key_node.remove(child)
            fifths_node = ET.SubElement(key_node, _qualified_name(key_node, "fifths"))
            fifths_node.text = str(fifths)
            mode_node = ET.SubElement(key_node, _qualified_name(key_node, "mode"))
            mode_node.text = mode


def _set_initial_time_signature(root: ET.Element, before_value: str, after_value: str) -> None:
    """Set the initial displayed meter and adjust full-measure staff backups."""

    before_beats, before_beat_type = _parse_time_signature(before_value)
    beats, beat_type = _parse_time_signature(after_value)
    parts = [node for node in list(root) if _local_name(node.tag) == "part"]
    if not parts:
        raise SourcePreservingPatchError("Source MusicXML does not contain a score part for the time-signature edit.")

    for part in parts:
        measures = [node for node in list(part) if _local_name(node.tag) == "measure"]
        if not measures:
            raise SourcePreservingPatchError("A source MusicXML part has no measure for the time-signature edit.")
        first_measure = measures[0]
        attributes_nodes: list[ET.Element] = []
        for child in list(first_measure):
            child_name = _local_name(child.tag)
            if child_name in {"note", "backup", "forward"}:
                break
            if child_name == "attributes":
                attributes_nodes.append(child)
        if not attributes_nodes:
            attributes = ET.Element(_qualified_name(first_measure, "attributes"))
            insert_at = 0
            while insert_at < len(first_measure) and _local_name(first_measure[insert_at].tag) == "print":
                insert_at += 1
            first_measure.insert(insert_at, attributes)
            attributes_nodes = [attributes]

        time_nodes = [
            child
            for attributes in attributes_nodes
            for child in list(attributes)
            if _local_name(child.tag) == "time"
        ]
        if not time_nodes:
            attributes = attributes_nodes[0]
            time_node = ET.Element(_qualified_name(attributes, "time"))
            _insert_before_first(attributes, time_node, {"staves", "part-symbol", "instruments", "clef"})
            time_nodes = [time_node]
        for time_node in time_nodes:
            for child in list(time_node):
                if _local_name(child.tag) in {"beats", "beat-type", "senza-misura"}:
                    time_node.remove(child)
            beats_node = ET.SubElement(time_node, _qualified_name(time_node, "beats"))
            beats_node.text = str(beats)
            beat_type_node = ET.SubElement(time_node, _qualified_name(time_node, "beat-type"))
            beat_type_node.text = str(beat_type)

        _adjust_full_measure_backups(
            measures,
            Fraction(before_beats * 4, before_beat_type),
            Fraction(beats * 4, beat_type),
        )


def _parse_time_signature(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", str(value or ""))
    if match is None:
        raise SourcePreservingPatchError(f"Unsupported source-preserving time signature: {value}")
    beats, beat_type = (int(match.group(1)), int(match.group(2)))
    if beats < 1 or beat_type < 1:
        raise SourcePreservingPatchError(f"Unsupported source-preserving time signature: {value}")
    return beats, beat_type


def _adjust_full_measure_backups(
    measures: list[ET.Element],
    old_capacity: Fraction,
    new_capacity: Fraction,
) -> None:
    """Resize only backups that represented the complete old measure span."""

    divisions = 1
    for measure in measures:
        for child in list(measure):
            if _local_name(child.tag) != "attributes":
                continue
            divisions_text = _child_text(child, "divisions")
            if divisions_text and divisions_text.isdigit():
                divisions = max(1, int(divisions_text))
        old_ticks = old_capacity * divisions
        new_ticks = new_capacity * divisions
        if old_ticks.denominator != 1 or new_ticks.denominator != 1:
            raise SourcePreservingPatchError(
                "The time-signature edit cannot be represented exactly with the source MusicXML divisions."
            )
        for backup in [child for child in list(measure) if _local_name(child.tag) == "backup"]:
            duration = _child(backup, "duration")
            if duration is not None and (duration.text or "").strip() == str(old_ticks.numerator):
                duration.text = str(new_ticks.numerator)


def _parse_key_signature(value: str) -> tuple[int, str]:
    normalized = (
        str(value or "")
        .strip()
        .replace("♭", "b")
        .replace("♯", "#")
        .replace("-flat", "b")
        .replace(" flat", "b")
        .replace("-sharp", "#")
        .replace(" sharp", "#")
    )
    match = re.fullmatch(r"([A-Ga-g])([#b]?)[ ]+(major|minor)", normalized, flags=re.IGNORECASE)
    if match is None:
        raise SourcePreservingPatchError(f"Unsupported source-preserving key signature: {value}")
    letter, accidental, mode = match.groups()
    tonic = letter.upper() + accidental
    mode = mode.lower()
    mapping = _MINOR_KEY_FIFTHS if mode == "minor" else _MAJOR_KEY_FIFTHS
    if tonic not in mapping:
        raise SourcePreservingPatchError(f"Unsupported source-preserving key signature: {value}")
    return mapping[tonic], mode


def _note_node_index(root: ET.Element) -> dict[str, _NoteNode]:
    result: dict[str, _NoteNode] = {}
    generated_index = 0
    parts = [node for node in list(root) if _local_name(node.tag) == "part"]
    for part in parts:
        divisions = 1
        measures = [node for node in list(part) if _local_name(node.tag) == "measure"]
        for measure_index, measure in enumerate(measures, start=1):
            try:
                measure_number = int(measure.get("number") or measure_index)
            except ValueError:
                measure_number = measure_index
            for child in list(measure):
                if _local_name(child.tag) != "attributes":
                    continue
                divisions_text = _child_text(child, "divisions")
                if divisions_text and divisions_text.isdigit():
                    divisions = max(1, int(divisions_text))
            for note in [child for child in list(measure) if _local_name(child.tag) == "note"]:
                generated_index += 1
                event_id = _technical_event_id(note) or f"m{measure_number}_e{generated_index}"
                staff_number = _child_text(note, "staff") or "1"
                staff = "left_hand" if staff_number == "2" else "right_hand"
                voice_text = _child_text(note, "voice") or "1"
                raw_voice = int(voice_text) if voice_text.isdigit() else 1
                voice = local_voice_from_musicxml(raw_voice)
                if event_id in result:
                    raise SourcePreservingPatchError(f"Duplicate source MusicXML event ID: {event_id}")
                result[event_id] = _NoteNode(event_id, measure_number, staff, voice, note, measure, divisions)
    return result


def _technical_event_id(note: ET.Element) -> str | None:
    for node in note.iter():
        if _local_name(node.tag) != "other-technical":
            continue
        value = (node.text or "").strip()
        if value.startswith("sera-event-id:"):
            return value.split(":", maxsplit=1)[1].strip() or None
    return None


def _set_pitch(note: ET.Element, pitch_value: str) -> None:
    match = _PITCH_RE.fullmatch(pitch_value.strip())
    if match is None:
        raise SourcePreservingPatchError(f"Unsupported compact pitch value: {pitch_value}")
    pitch = _child(note, "pitch")
    if pitch is None:
        raise SourcePreservingPatchError("A pitch edit targeted a rest or unpitched MusicXML note.")
    step, accidental_text, octave = match.groups()
    alter = accidental_text.count("#") - accidental_text.count("b")
    step_node = _child(pitch, "step")
    octave_node = _child(pitch, "octave")
    if step_node is None or octave_node is None:
        raise SourcePreservingPatchError("The source MusicXML pitch is missing step or octave.")
    step_node.text = step.upper()
    octave_node.text = octave
    alter_node = _child(pitch, "alter")
    if alter:
        if alter_node is None:
            alter_node = ET.Element(_qualified_name(pitch, "alter"))
            pitch.insert(list(pitch).index(octave_node), alter_node)
        alter_node.text = str(alter)
    elif alter_node is not None:
        pitch.remove(alter_node)
    accidental_node = _child(note, "accidental")
    if accidental_node is not None:
        if accidental_text:
            accidental_node.text = {
                "#": "sharp",
                "##": "double-sharp",
                "b": "flat",
                "bb": "flat-flat",
            }.get(accidental_text, accidental_node.text)
        else:
            note.remove(accidental_node)


def _set_articulations(note: ET.Element, values: list[str]) -> None:
    notations = _child(note, "notations")
    if notations is None:
        notations = ET.SubElement(note, _qualified_name(note, "notations"))
    articulations = _child(notations, "articulations")
    if articulations is None:
        articulations = ET.SubElement(notations, _qualified_name(notations, "articulations"))
    requested = {str(value).strip().lower().replace("_", "-") for value in values if str(value).strip()}
    supported = {"staccato", "accent", "tenuto"}
    unknown = sorted(requested - supported)
    if unknown:
        raise SourcePreservingPatchError("Unsupported source-preserving articulations: " + ", ".join(unknown))
    for child in list(articulations):
        if _local_name(child.tag) in supported:
            articulations.remove(child)
    for value in sorted(requested):
        ET.SubElement(articulations, _qualified_name(articulations, value))
    if not list(articulations):
        notations.remove(articulations)
    if not list(notations):
        note.remove(notations)


def _dynamic_boundary_marks(
    after_index: dict[str, Any],
    changed_ids: set[str],
) -> list[tuple[str, str]]:
    """Return target and restoration marks for persistent MusicXML dynamics."""

    if not changed_ids:
        return []
    lanes: dict[tuple[str, str, int], list[Any]] = {}
    for context in after_index.values():
        if context.event.get("type") != "note":
            continue
        lanes.setdefault((context.part_id, context.staff, context.voice), []).append(context)
    marks: list[tuple[str, str]] = []
    for contexts in lanes.values():
        contexts.sort(
            key=lambda context: (
                context.measure,
                context.offset,
                bool(context.event.get("is_chord_tone")),
                context.event_id,
            )
        )
        active_override: str | None = None
        for context in contexts:
            desired = str(context.event.get("dynamic", "")).strip().lower()
            if context.event_id in changed_ids:
                if desired != active_override:
                    marks.append((context.event_id, desired))
                active_override = desired
            elif active_override is not None:
                if desired != active_override:
                    marks.append((context.event_id, desired))
                active_override = None
    return marks


def _set_note_dynamic(note: ET.Element, dynamic: str) -> None:
    if not re.fullmatch(r"p{1,2}|mp|mf|f{1,2}", dynamic):
        raise SourcePreservingPatchError(f"Unsupported source-preserving dynamic: {dynamic}")
    notations = _child(note, "notations")
    if notations is None:
        notations = ET.SubElement(note, _qualified_name(note, "notations"))
    dynamics = _child(notations, "dynamics")
    if dynamics is None:
        dynamics = ET.SubElement(notations, _qualified_name(notations, "dynamics"))
    for child in list(dynamics):
        dynamics.remove(child)
    ET.SubElement(dynamics, _qualified_name(dynamics, dynamic))


def _insert_dynamic_direction(node: _NoteNode, dynamic: str) -> None:
    if not re.fullmatch(r"p{1,2}|mp|mf|f{1,2}", dynamic):
        raise SourcePreservingPatchError(f"Unsupported source-preserving dynamic: {dynamic}")
    measure_children = list(node.measure_node)
    note_position = measure_children.index(node.note)
    direction = ET.Element(_qualified_name(node.measure_node, "direction"), {"placement": "below"})
    direction_type = ET.SubElement(direction, _qualified_name(direction, "direction-type"))
    dynamics = ET.SubElement(direction_type, _qualified_name(direction_type, "dynamics"))
    ET.SubElement(dynamics, _qualified_name(dynamics, dynamic))
    staff = ET.SubElement(direction, _qualified_name(direction, "staff"))
    staff.text = "2" if node.staff == "left_hand" else "1"
    direction.tail = node.note.tail
    node.measure_node.insert(note_position, direction)


def _set_title_and_composer(root: ET.Element, before: dict[str, Any], after: dict[str, Any]) -> None:
    if str(before.get("title", "")) != str(after.get("title", "")):
        work = next((node for node in root.iter() if _local_name(node.tag) == "work"), None)
        if work is None:
            work = ET.Element(_qualified_name(root, "work"))
            root.insert(0, work)
        title = _child(work, "work-title")
        if title is None:
            title = ET.SubElement(work, _qualified_name(work, "work-title"))
        title.text = str(after.get("title") or "Untitled Sera Score")
    if str(before.get("composer", "")) != str(after.get("composer", "")):
        identification = next((node for node in root.iter() if _local_name(node.tag) == "identification"), None)
        if identification is None:
            identification = ET.Element(_qualified_name(root, "identification"))
            root.insert(1, identification)
        creator = next(
            (
                node
                for node in identification
                if _local_name(node.tag) == "creator" and node.get("type") == "composer"
            ),
            None,
        )
        if creator is None:
            creator = ET.SubElement(
                identification,
                _qualified_name(identification, "creator"),
                {"type": "composer"},
            )
        creator.text = str(after.get("composer") or "Sera")


def _note_order(node: _NoteNode) -> int:
    return list(node.measure_node).index(node.note)


def _serialize_with_original_prolog(source: str, root: ET.Element) -> str:
    namespace = _namespace(root.tag)
    if namespace:
        ET.register_namespace("", namespace)
    declaration = re.search(r"<\?xml[^?]*\?>", source)
    doctype = re.search(r"<!DOCTYPE[^>]*>", source, flags=re.IGNORECASE)
    pieces = []
    if declaration:
        pieces.append(declaration.group(0))
    else:
        pieces.append('<?xml version="1.0" encoding="UTF-8"?>')
    if doctype:
        pieces.append(doctype.group(0))
    pieces.append(ET.tostring(root, encoding="unicode", short_empty_elements=True))
    return "\n".join(pieces) + "\n"


def _child(parent: ET.Element, name: str) -> ET.Element | None:
    return next((node for node in list(parent) if _local_name(node.tag) == name), None)


def _child_text(parent: ET.Element, name: str) -> str | None:
    node = _child(parent, name)
    return None if node is None else (node.text or "").strip()


def _local_name(tag: str) -> str:
    return str(tag).rsplit("}", maxsplit=1)[-1]


def _namespace(tag: str) -> str:
    value = str(tag)
    return value[1:].split("}", maxsplit=1)[0] if value.startswith("{") else ""


def _qualified_name(parent: ET.Element, name: str) -> str:
    namespace = _namespace(parent.tag)
    return f"{{{namespace}}}{name}" if namespace else name

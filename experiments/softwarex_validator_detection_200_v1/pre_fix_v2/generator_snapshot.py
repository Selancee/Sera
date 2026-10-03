"""Measure transaction error detection using independently specified mutations."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.score_document_service import normalize_score_document
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.domain.score_scope import iter_event_contexts
from sera_edit.execution.transaction import PatchTransaction
from evaluation.runners.experiment_runner import _git_metadata


def cases(score: dict):
    notes = [c for c in iter_event_contexts(score) if c.event.get("type") == "note" and not c.event.get("tie") and not c.event.get("slur")]
    # Independent representability precondition: a single note at its onset,
    # not one member of a chord (MusicXML dynamics are staff directions).
    contexts = list(iter_event_contexts(score))
    anchor = next(c for c in notes if not c.event.get("is_chord_tone") and not c.event.get("chord_group_id")
                  and sum(d.measure == c.measure and d.staff == c.staff and d.offset == c.offset for d in contexts) == 1)
    other = next(c for c in notes if c.staff != anchor.staff)
    wanted = "f" if anchor.event.get("dynamic") != "f" else "p"
    patch = {"schema_version": "1.0.0", "patch_id": "detection-control", "source_score_id": score["score_id"],
             "source_fingerprint": score_fingerprint(score), "instruction": f"Set only {anchor.event_id} to {wanted}; preserve pitch and duration.",
             "target_scope": {"event_ids": [anchor.event_id]}, "protected_scope": {"event_ids": [other.event_id]},
             "preconditions": [], "expected_effects": [], "provenance": {"provider": "mutation_study"},
             "operations": [{"operation_id": "op1", "type": "set_dynamic", "selector": {"event_ids": [anchor.event_id]},
                             "arguments": {"dynamic": wanted}, "preconditions": []}]}
    # Labels come from the construction below, never the detector's result.
    yield "valid_dynamic", False, patch, "The selected existing note changes only to the requested dynamic."
    p = copy.deepcopy(patch); p.pop("schema_version")
    yield "missing_schema", True, p, "Required schema_version field removed."
    p = copy.deepcopy(patch); p["source_fingerprint"] = "sha256:" + "0" * 64
    assert p["source_fingerprint"] != score_fingerprint(score)
    yield "stale_source", True, p, "Fingerprint differs from source."
    p = copy.deepcopy(patch); p["operations"][0]["selector"] = {"event_ids": ["__absent_mutation_event__"]}
    assert not any(c.event_id == "__absent_mutation_event__" for c in iter_event_contexts(score))
    yield "missing_event", True, p, "Selector names an absent event."
    p = copy.deepcopy(patch); p["operations"][0]["selector"] = {"event_ids": [other.event_id]}
    yield "protected_edit", True, p, "Operation targets the explicitly protected note outside target scope."
    for family, operation, arguments, reason in (
        ("duration_overflow", "set_duration", {"duration": "whole"}, "A non-whole note becomes a whole note without moving subsequent events."),
        ("orphan_tie", "set_tie", {"tie": "stop"}, "A tie stop is inserted on the first untied note."),
        ("orphan_slur", "set_slur", {"slur": "stop"}, "A slur stop is inserted on the first unslurred note."),
        ("preserve_pitch_violation", "set_pitch", {"pitch": "C7" if anchor.event.get("pitch") != "C7" else "D7"}, "Pitch changes despite an explicit preserve_pitch postcondition."),
    ):
        p = copy.deepcopy(patch)
        p["operations"][0].update(type=operation, arguments=arguments)
        if family == "duration_overflow":
            assert anchor.event["duration"] != "whole"
        if family == "preserve_pitch_violation":
            p["expected_effects"] = [{"type": "preserve_pitch"}]
        yield family, True, p, reason
    p = copy.deepcopy(patch); p["operations"][0]["arguments"]["dynamic"] = "pp" if wanted != "pp" else "ff"
    p["expected_effects"] = [{"type": "dynamic_equals", "event_id": anchor.event_id, "value": wanted}]
    yield "wrong_dynamic_semantics", True, p, "Output dynamic differs from both instruction and declared dynamic_equals effect."


def run(output: Path) -> dict:
    if output.exists():
        raise ValueError("Refusing to overwrite existing study evidence")
    provenance = _git_metadata()
    output.mkdir(parents=True)
    rows = []
    sources = {}
    for path in sorted((ROOT / "benchmark/source_scores").glob("*.score.json")):
        sources[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        source = normalize_score_document(json.loads(path.read_text(encoding="utf-8")))
        for family, invalid, patch, oracle in cases(source):
            before = copy.deepcopy(source)
            try:
                result = PatchTransaction().execute(source, patch)
                caught = not result.committed and bool(result.report.errors)
                unchanged = source == before
                rollback = not result.committed and score_fingerprint(result.score_document) == score_fingerprint(before)
                data = result.as_dict()
                error = None
            except Exception as exc:
                caught, unchanged, rollback = False, source == before, False
                data, error = None, f"{type(exc).__name__}: {exc}"
            row = {"case_id": f"{source['score_id']}:{family}", "family": family, "invalid": invalid,
                   "oracle": oracle, "patch": patch, "detected": caught, "caller_unchanged": unchanged,
                   "rollback_verified": rollback, "result": data, "exception": error}
            rows.append(row)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["family"]].append(row)
    summary = {"created_at": datetime.now(UTC).isoformat(), "git": provenance, "source_hashes": sources,
               "source_count": len(sources), "case_count": len(rows), "families": {},
               "scope": "Constructed mutation detection on existing synthetic sources; not model error prevalence or generalization."}
    for family, group in sorted(grouped.items()):
        invalid = group[0]["invalid"]
        detected = sum(r["detected"] for r in group)
        summary["families"][family] = {"n": len(group), "invalid": invalid, "rejected": detected,
            "detection_rate" if invalid else "false_positive_rate": detected / len(group),
            "exceptions": sum(r["exception"] is not None for r in group),
            "caller_unchanged": sum(r["caller_unchanged"] for r in group),
            "rollback_verified": sum(r["rollback_verified"] for r in group)}
    evidence = output / "cases.jsonl"
    evidence.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    summary["cases_sha256"] = hashlib.sha256(evidence.read_bytes()).hexdigest()
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))

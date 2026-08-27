"""Audit source/revision MusicXML with Composer V0.4 symbolic proxies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.generation.musicality.melody_expectation_validator import validate_melody_expectation
from backend.services.score_document_service import musicxml_to_score_document
from sera_edit.composer.phrase_analysis import analyze_phrase
from sera_edit.composer.pipeline import generate_composition_candidates
from sera_edit.composer.texture_analysis import analyze_texture
from sera_edit.domain.score_scope import ScoreScope


def audit(path: Path, measures: list[int]) -> dict[str, Any]:
    score = musicxml_to_score_document(path.read_text(encoding="utf-8"), source="composer_audit")
    scope = {"measures": measures}
    phrase = analyze_phrase(score, scope)
    primary_voice = str(phrase.get("primary_voice_id") or "")
    contexts = [
        context
        for context in ScoreScope.from_dict(scope).select(score)
        if context.event.get("type") == "note" and f"{context.staff}:v{context.voice}" == primary_voice
    ]
    events = [
        {
            "type": "note",
            "pitch": context.event.get("pitch"),
            "duration": context.event.get("duration"),
            "offset": float(context.offset),
            "measure": context.measure,
        }
        for context in contexts
    ]
    return {
        "path": str(path.resolve()),
        "score_id": score.get("score_id"),
        "key": (score.get("global") or {}).get("key"),
        "measures": measures,
        "texture": analyze_texture(score, scope),
        "phrase": {
            "primary_voice_id": phrase.get("primary_voice_id"),
            "contour": (phrase.get("source_motif") or {}).get("contour"),
            "intervals": (phrase.get("source_motif") or {}).get("intervals"),
            "selected_note_count": phrase.get("selected_note_count"),
        },
        "melodic_expectation": validate_melody_expectation(
            events,
            key=str((score.get("global") or {}).get("key") or "C major"),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit MusicXML with Composer V0.4 texture and melody-expectation proxies.")
    parser.add_argument("source", type=Path, help="Source MusicXML file.")
    parser.add_argument("--revision", type=Path, help="Optional reviewed MusicXML revision.")
    parser.add_argument("--measures", type=int, nargs="+", required=True, help="One or more selected measure numbers.")
    parser.add_argument("--brief", help="Optional local Composer brief to replay without calling an LLM.")
    args = parser.parse_args()
    payload = {"source": audit(args.source, args.measures)}
    if args.revision:
        payload["revision"] = audit(args.revision, args.measures)
    if args.brief:
        source_score = musicxml_to_score_document(args.source.read_text(encoding="utf-8"), source="composer_replay")
        replay = generate_composition_candidates(
            source_score,
            args.brief,
            {"measures": args.measures},
            {},
            candidate_count=3,
            search_width=16,
        )
        payload["local_replay"] = {
            "status": replay["status"],
            "reason": replay["reason"],
            "failure_analysis": replay.get("failure_analysis"),
            "plan": replay["plan"],
            "texture_analysis": replay["texture_analysis"],
            "retrieval": (replay.get("style_knowledge") or {}).get("retrieval"),
            "selected_rule_ids": [
                item.get("rule_id") for item in (replay.get("style_knowledge") or {}).get("matched_rules") or []
            ],
            "candidates": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "rank": candidate["rank"],
                    "review": {
                        key: candidate["review"].get(key)
                        for key in (
                            "overall_score",
                            "theory_score",
                            "melody_expectation_score",
                            "source_melody_expectation_score",
                            "melody_expectation_delta",
                            "melody_expectation_preservation",
                            "large_leap_count",
                            "changed_event_count",
                            "texture_structure_preserved",
                        )
                    },
                }
                for candidate in replay.get("candidates") or []
            ],
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

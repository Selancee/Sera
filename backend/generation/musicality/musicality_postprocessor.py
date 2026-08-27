"""Postprocess weak symbolic generations into V0.9 musicality constraints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.generation.musicality.generation_profile import GenerationProfile


class MusicalityPostprocessor:
    def repair_score_document(self, score: dict[str, Any], profile: GenerationProfile) -> tuple[dict[str, Any], dict[str, Any]]:
        repaired = json.loads(json.dumps(score))
        actions: list[str] = []
        if self._only_quarters(repaired, profile):
            for measure in repaired.get("measures", []):
                right = [event for event in measure.get("events", []) if event.get("staff") != "left_hand"]
                for index, event in enumerate(right):
                    if index % 2 == 0:
                        event["duration"] = "eighth"
                actions.append("replaced excessive quarter notes with eighth-note motion")
                break
        if profile.requires_accompaniment and not self._has_left_hand(repaired):
            for measure in repaired.get("measures", []):
                measure.setdefault("events", []).append(
                    {
                        "event_id": f"{measure.get('measure_id', 'm')}_lh_v09",
                        "type": "note",
                        "pitch": "C3",
                        "duration": "half",
                        "offset": 0.0,
                        "voice": 1,
                        "staff": "left_hand",
                        "tie": None,
                        "dynamic": "mp",
                        "articulations": [],
                        "selected": False,
                    }
                )
            actions.append("added sparse left-hand accompaniment")
        if profile.requires_cadence and repaired.get("measures"):
            repaired["measures"][-1]["cadence"] = "authentic"
            repaired["measures"][-1]["harmony"] = "i" if "minor" in profile.key.lower() else "I"
            actions.append("ensured final cadence metadata")
        report = {
            "engine": "musicality_postprocessor_v09",
            "actions": actions,
            "fixed_consecutive_quarters": any("quarter" in action for action in actions),
            "added_accompaniment": any("accompaniment" in action for action in actions),
            "added_cadence": any("cadence" in action for action in actions),
        }
        return repaired, report

    def report_for_generated_metadata(self, profile: GenerationProfile, metadata: dict[str, Any]) -> dict[str, Any]:
        rhythm = metadata.get("rhythm_patterns", {})
        return {
            "engine": "musicality_postprocessor_v09",
            "actions": ["v09 musicality engines applied before MusicXML assembly"],
            "used_processed_musicxml": False,
            "fixed_consecutive_quarters": False,
            "added_accompaniment": bool(profile.requires_accompaniment),
            "added_cadence": bool(profile.requires_cadence),
            "rhythmic_variety_ok": int(rhythm.get("unique_pattern_count", 0) or 0) >= profile.min_rhythmic_variety,
        }

    @staticmethod
    def write_report(path: str | Path, report: dict[str, Any]) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @staticmethod
    def _only_quarters(score: dict[str, Any], profile: GenerationProfile) -> bool:
        durations = [event.get("duration") for measure in score.get("measures", []) for event in measure.get("events", []) if event.get("type") == "note"]
        if not durations:
            return False
        return len([duration for duration in durations if duration == "quarter"]) > profile.max_consecutive_quarters and len(set(durations)) == 1

    @staticmethod
    def _has_left_hand(score: dict[str, Any]) -> bool:
        return any(event.get("staff") == "left_hand" for measure in score.get("measures", []) for event in measure.get("events", []))

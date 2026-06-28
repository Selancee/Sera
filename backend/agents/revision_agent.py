"""Revision Agent for repairing and steering symbolic outputs."""

from __future__ import annotations

from copy import deepcopy

from backend.agents.composition_planning_agent import CompositionPlanningAgent
from backend.models.schemas import CompositionPlan, ValidationResult


class RevisionAgent:
    """Apply conservative rule-based revisions after validation or feedback."""

    def revise(
        self,
        plan: CompositionPlan,
        validation: ValidationResult,
        feedback: str | None = None,
    ) -> tuple[CompositionPlan, dict[str, object]]:
        """Return a revised plan and an audit trail.

        TODO: Replace this semi-rule agent with a JSON-schema-constrained LLM
        reviser that edits only targeted measures once enough failure cases are
        logged for prompt tuning.
        """

        original = plan
        revised = deepcopy(plan)
        changes: list[str] = []
        feedback_text = (feedback or "").lower()
        requires_replan = False

        if not validation.valid:
            issue_text = " ".join(validation.issues).lower()
            if "empty measure" in issue_text or "no pitched notes" in issue_text:
                for measure in revised.measures:
                    if not measure.notes:
                        measure.notes = ["1", "2", "3", "5"]
                changes.append("replaced empty measures with the default motif")
            if "incomplete duration" in issue_text or "duration" in issue_text:
                revised.intent.revision_goals.append("regenerate complete measures")
                requires_replan = True
                changes.append("requested full-measure rhythmic regeneration")
            if "pitch" in issue_text and "outside" in issue_text:
                revised.intent.revision_goals.append("keep pitches inside instrument range")
                revised.intent.difficulty = "beginner"
                requires_replan = True
                changes.append("lowered difficulty to reduce pitch range risk")
            if "parse error" in issue_text:
                revised.intent.revision_goals.append("regenerate parseable MusicXML")
                requires_replan = True
                changes.append("requested MusicXML regeneration from structured plan")

        if feedback_text:
            requires_replan |= self._apply_feedback(revised, feedback_text, changes)

        if requires_replan:
            revised = CompositionPlanningAgent().plan(revised.intent)

        if not changes:
            changes.append("no structural repair required")

        return revised, {
            "agent": "revision_agent_v0_2",
            "feedback": feedback or "",
            "changes": changes,
            "valid_before_revision": validation.valid,
            "old_plan_summary": {
                "title": original.intent.title,
                "key": original.intent.key,
                "meter": original.intent.time_signature,
                "tempo": original.intent.tempo_bpm,
                "length_measures": original.intent.bars,
                "texture": original.intent.texture,
            },
            "new_plan_summary": {
                "title": revised.intent.title,
                "key": revised.intent.key,
                "meter": revised.intent.time_signature,
                "tempo": revised.intent.tempo_bpm,
                "length_measures": revised.intent.bars,
                "texture": revised.intent.texture,
            },
        }

    @staticmethod
    def _apply_feedback(revised: CompositionPlan, feedback_text: str, changes: list[str]) -> bool:
        intent = revised.intent
        requires_replan = False

        if "更忧郁" in feedback_text or "more melancholic" in feedback_text or "sad" in feedback_text:
            intent.mood = "melancholic"
            if "minor" not in intent.key.lower():
                intent.key = "A minor"
            intent.tempo_bpm = min(intent.tempo_bpm, 76)
            intent.harmony_plan = ["i", "VI", "iv", "V"]
            changes.append("updated mood/key/harmony toward a melancholic minor plan")
            requires_replan = True

        if "肖邦" in feedback_text or "chopin" in feedback_text:
            intent.style = "romantic"
            intent.texture = "arpeggiated"
            intent.title = f"Nocturne in {intent.key}"
            intent.tempo_bpm = min(intent.tempo_bpm, 88)
            intent.harmony_plan = ["i", "VI", "iv", "V"] if "minor" in intent.key.lower() else ["I", "vi", "ii", "V"]
            changes.append("shifted style toward a Chopin-like romantic piano nocturne")
            requires_replan = True

        if "三拍" in feedback_text or "3/4" in feedback_text or "waltz" in feedback_text:
            intent.time_signature = "3/4"
            intent.form = "ABA" if intent.bars >= 16 else "AB"
            changes.append("changed meter to 3/4")
            requires_replan = True

        if "6/8" in feedback_text or "六八" in feedback_text:
            intent.time_signature = "6/8"
            changes.append("changed meter to 6/8")
            requires_replan = True

        if "降低难度" in feedback_text or "simpl" in feedback_text or "easier" in feedback_text:
            intent.difficulty = "beginner"
            intent.texture = "melody_accompaniment"
            intent.tempo_bpm = min(intent.tempo_bpm, 96)
            for measure in revised.measures:
                measure.density = "low" if measure.index % 4 == 0 else "medium"
                measure.rhythm = "simple quarter-note pulse"
            changes.append("lowered difficulty and simplified texture")
            requires_replan = True

        if "加快" in feedback_text or "faster" in feedback_text or "快一点" in feedback_text:
            intent.tempo_bpm = min(220, intent.tempo_bpm + 20)
            changes.append("increased tempo")

        if "左手更流动" in feedback_text or "flowing left hand" in feedback_text or "left hand more flowing" in feedback_text:
            intent.texture = "arpeggiated"
            intent.revision_goals.append("left hand arpeggiated motion")
            changes.append("changed texture to arpeggiated left-hand motion")
            requires_replan = True

        return requires_replan

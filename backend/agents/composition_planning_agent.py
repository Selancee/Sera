"""Composition Planning Agent for measure-level symbolic plans."""

from __future__ import annotations

from backend.models.schemas import CompositionPlan, MeasurePlan, StructuredMusicIntent, validate_agent_plan_json


DIATONIC_PROGRESSIONS = {
    "major": ["I", "vi", "IV", "V", "I", "ii", "V", "I"],
    "minor": ["i", "VI", "iv", "V", "i", "iv", "V", "i"],
}
JAZZ_PROGRESSIONS = ["ii7", "V7", "Imaj7", "VI7", "ii7", "V7", "Imaj7", "Imaj7"]


class CompositionPlanningAgent:
    """Create a phrase, harmony, and texture plan from a structured intent."""

    def plan(self, intent: StructuredMusicIntent) -> CompositionPlan:
        """Return a measure-level plan constrained to 8, 16, or 32 measures."""

        bars = intent.bars if intent.bars in {8, 16, 32} else 16
        mode = "minor" if "minor" in intent.key.lower() else "major"
        progression = self._progression_for_intent(intent, mode)
        sections = self._sections_for_form(intent.form, bars)
        section_ranges = self._section_plan_from_sections(sections)
        intent.section_plan = section_ranges

        measures: list[MeasurePlan] = []
        section_end_indexes = {self._range_end(item["measures"]) for item in section_ranges}
        phrase_end_indexes = set(range(4, bars + 1, 4)) | section_end_indexes

        for index in range(1, bars + 1):
            section = sections[index - 1]
            chord = progression[(index - 1) % len(progression)]
            cadence = ""
            if index == bars:
                cadence = "authentic cadence"
                chord = "i" if mode == "minor" else "I"
            elif index in phrase_end_indexes:
                cadence = "half cadence" if index < bars else "authentic cadence"
                if cadence == "half cadence":
                    chord = "V"
            rhythm = self._rhythm_for_signature(intent.time_signature, index, intent.texture, cadence)
            density = self._density_for_index(index, bars, intent.mood, intent.difficulty)
            measures.append(
                MeasurePlan(
                    index=index,
                    section=section,
                    chord=chord,
                    function=self._function_for_chord(chord),
                    rhythm=rhythm,
                    density=density,
                    cadence=cadence,
                    notes=self._motif_hint(index, mode, section, cadence),
                    texture=intent.texture,
                    description=self._measure_description(section, index, bars, cadence),
                )
            )

        agent_json = intent.to_agent_plan_json()
        schema_valid, schema_errors = validate_agent_plan_json(agent_json)
        global_plan = {
            "form": intent.form,
            "phrase_lengths": self._phrase_lengths(bars),
            "orchestration": intent.instruments,
            "texture": intent.texture,
            "harmony": intent.harmony,
            "harmony_plan": progression,
            "section_plan": section_ranges,
            "schema_valid": schema_valid,
            "schema_errors": schema_errors,
            "revision_targets": [
                "valid MusicXML",
                "complete measures",
                "comfortable pitch range",
                "prompt-plan consistency",
            ],
            # TODO: make this phrase graph editable in the UI for user-directed
            # planning experiments instead of regenerating the whole plan.
            "planning_notes": "Rule-based V0.2 phrase graph with deterministic motif repetition and variation.",
        }
        return CompositionPlan(intent=intent, measures=measures, global_plan=global_plan, baseline="rule_based_v0_2")

    @staticmethod
    def _progression_for_intent(intent: StructuredMusicIntent, mode: str) -> list[str]:
        if intent.style == "jazz":
            return JAZZ_PROGRESSIONS
        if intent.harmony_plan:
            return intent.harmony_plan
        return DIATONIC_PROGRESSIONS[mode]

    @staticmethod
    def _sections_for_form(form: str, bars: int) -> list[str]:
        normalized = (form or "AB").replace(" ", "")
        if normalized.lower().startswith("theme"):
            labels = ["T", "V1", "V2", "Coda"] if bars == 32 else ["T", "V1"]
        elif normalized.upper() == "AABA":
            labels = ["A", "A", "B", "A"]
        elif normalized.upper() == "ABA":
            labels = ["A", "B", "A"]
        elif normalized.upper() == "AB":
            labels = ["A", "B"]
        else:
            labels = [char for char in normalized.upper() if char.isalpha()] or ["A", "B"]

        base = bars // len(labels)
        remainder = bars % len(labels)
        sections: list[str] = []
        for idx, label in enumerate(labels):
            length = base + (1 if idx < remainder else 0)
            sections.extend([label] * length)
        return sections[:bars]

    @staticmethod
    def _section_plan_from_sections(sections: list[str]) -> list[dict[str, str]]:
        plan: list[dict[str, str]] = []
        start = 1
        current = sections[0]
        for index, label in enumerate(sections + ["__END__"], start=1):
            if label != current:
                end = index - 1
                plan.append(
                    {
                        "section": current,
                        "measures": f"{start}-{end}",
                        "description": CompositionPlanningAgent._section_description(current, start, end),
                    }
                )
                start = index
                current = label
        return plan

    @staticmethod
    def _range_end(range_text: str) -> int:
        return int(range_text.split("-")[-1])

    @staticmethod
    def _section_description(label: str, start: int, end: int) -> str:
        if label == "A":
            return "theme presentation" if start == 1 else "theme return with variation"
        if label == "B":
            return "contrasting middle section"
        if label.startswith("V"):
            return "theme variation"
        if label == "T":
            return "theme statement"
        return f"section {label} measures {start}-{end}"

    @staticmethod
    def _phrase_lengths(bars: int) -> list[int]:
        return [4] * (bars // 4)

    @staticmethod
    def _rhythm_for_signature(time_signature: str, index: int, texture: str, cadence: str) -> str:
        if cadence:
            return "cadential long-short closure"
        if time_signature == "3/4":
            return "three quarter pulses" if index % 2 else "half plus quarter"
        if time_signature == "6/8":
            return "compound 3+3 eighth motion" if texture == "arpeggiated" else "dotted-quarter pulse"
        if texture == "arpeggiated":
            return "eighth arpeggio under quarter melody"
        return "four quarter-note melody tones" if index % 2 else "two half-note anchors"

    @staticmethod
    def _density_for_index(index: int, bars: int, mood: str, difficulty: str) -> str:
        if difficulty == "beginner":
            return "low" if index % 4 == 0 else "medium"
        if difficulty == "advanced":
            return "high" if index > bars // 3 else "medium"
        if index == bars:
            return "cadential"
        if mood == "energetic" and index > bars // 2:
            return "high"
        if index % 4 == 0:
            return "low"
        return "medium"

    @staticmethod
    def _function_for_chord(chord: str) -> str:
        root = chord.replace("7", "").replace("maj", "").lower()
        if root == "i":
            return "tonic"
        if root == "v":
            return "dominant"
        if root in {"iv", "ii"}:
            return "predominant"
        if root in {"vi", "vi"}:
            return "tonic prolongation"
        if chord in {"I", "Imaj7"}:
            return "tonic"
        return "color"

    @staticmethod
    def _motif_hint(index: int, mode: str, section: str, cadence: str) -> list[str]:
        major = [
            ["1", "2", "3", "5"],
            ["5", "3", "2", "1"],
            ["3", "4", "5", "6"],
            ["5", "4", "2", "1"],
        ]
        minor = [
            ["1", "2", "b3", "5"],
            ["5", "b3", "2", "1"],
            ["b3", "4", "5", "b6"],
            ["5", "4", "7", "1"],
        ]
        if cadence == "authentic cadence":
            return ["5", "4", "2", "1"] if mode == "major" else ["5", "4", "7", "1"]
        source = minor if mode == "minor" else major
        motif = list(source[(index - 1) % len(source)])
        if section == "B":
            motif = motif[1:] + motif[:1]
        elif index > 8 and section == "A":
            motif = [motif[0], motif[2], motif[1], motif[3]]
        return motif

    @staticmethod
    def _measure_description(section: str, index: int, bars: int, cadence: str) -> str:
        if cadence == "authentic cadence":
            return "final cadence and closure"
        if cadence:
            return "phrase cadence"
        if index <= 4:
            return "opening motif"
        if section == "B":
            return "contrasting motivic variation"
        if index > bars - 4:
            return "return preparation"
        return "motif repetition and development"

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
        section_ranges = self._add_section_controls(section_ranges, intent)
        intent.section_plan = section_ranges
        intent.rhythmic_density = self._density_for_index(1, bars, intent.mood, intent.difficulty)
        intent.melodic_contour = self._contour_for_section(sections[0], 1, bars)
        intent.interval_profile = "mixed"
        intent.cadence = "authentic"
        intent.polyphony = "chordal" if intent.texture == "chordal" else "monophonic"
        intent.tension = "medium"
        intent.motif_id = "A"
        intent.motif_strategy = "repeat"

        measures: list[MeasurePlan] = []
        section_end_indexes = {self._range_end(item["measures"]) for item in section_ranges}
        phrase_end_indexes = set(range(4, bars + 1, 4)) | section_end_indexes

        for index in range(1, bars + 1):
            section = sections[index - 1]
            chord = progression[(index - 1) % len(progression)]
            cadence = "none"
            if index == bars:
                cadence = "authentic"
                chord = "i" if mode == "minor" else "I"
            elif index in phrase_end_indexes:
                cadence = "half" if index < bars else "authentic"
                if cadence == "half":
                    chord = "V"
            rhythm = self._rhythm_for_signature(intent.time_signature, index, intent.texture, cadence)
            density = self._density_for_index(index, bars, intent.mood, intent.difficulty)
            contour = self._contour_for_section(section, index, bars)
            interval_profile = self._interval_profile_for_index(index, contour, intent.difficulty)
            motif_strategy = self._motif_strategy(index, section, cadence)
            measures.append(
                MeasurePlan(
                    index=index,
                    section=section,
                    chord=chord,
                    function=self._function_for_chord(chord),
                    rhythm=rhythm,
                    density=density,
                    cadence=cadence,
                    rhythmic_density=density if density in {"low", "medium", "high"} else "low",
                    melodic_contour=contour,
                    interval_profile=interval_profile,
                    polyphony="chordal" if intent.texture == "chordal" else "monophonic",
                    tension="high" if chord in {"V", "V7"} or cadence == "half" else "low" if cadence == "authentic" else "medium",
                    motif_id="cadence" if cadence != "none" else ("B" if section == "B" else "A"),
                    motif_strategy=motif_strategy,
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
            "v05_controls": {
                "rhythmic_density": "planned per section and measure",
                "melodic_contour": "planned per section and measure",
                "cadence": "half cadences at phrase ends, authentic cadence at final bar",
                "model_task_type": "melody_fragment",
            },
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
            "planning_notes": "V0.5 phrase graph with explicit rhythmic density, contour, cadence, and motif controls.",
        }
        return CompositionPlan(intent=intent, measures=measures, global_plan=global_plan, baseline="rule_based_v0_5_plan")

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
    def _add_section_controls(section_ranges: list[dict[str, str]], intent: StructuredMusicIntent) -> list[dict[str, str]]:
        controlled: list[dict[str, str]] = []
        for index, section in enumerate(section_ranges):
            label = section["section"]
            controls = dict(section)
            controls["rhythmic_density"] = "high" if label == "B" and intent.difficulty != "beginner" else "medium"
            controls["melodic_contour"] = "arch" if label == "A" else "wave"
            controls["cadence"] = "authentic" if index == len(section_ranges) - 1 else "half"
            controls["motif_strategy"] = "sequence_up" if label == "B" else "repeat"
            controlled.append(controls)
        return controlled

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
        if cadence != "none":
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
            return "low"
        if mood == "energetic" and index > bars // 2:
            return "high"
        if index % 4 == 0:
            return "low"
        return "medium"

    @staticmethod
    def _contour_for_section(section: str, index: int, bars: int) -> str:
        if index > bars - 4:
            return "descending"
        if section == "B":
            return "wave"
        if index % 4 in {1, 2}:
            return "ascending"
        if index % 4 == 3:
            return "arch"
        return "descending"

    @staticmethod
    def _interval_profile_for_index(index: int, contour: str, difficulty: str) -> str:
        if difficulty == "beginner":
            return "stepwise"
        if contour in {"arch", "wave"} or index % 3 == 0:
            return "mixed"
        if difficulty == "advanced" and index % 5 == 0:
            return "leaping"
        return "mixed"

    @staticmethod
    def _motif_strategy(index: int, section: str, cadence: str) -> str:
        if cadence != "none":
            return "cadence"
        if section == "B":
            return "sequence_up" if index % 2 else "sequence_down"
        if index > 8:
            return "rhythmic_variation"
        return "repeat"

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
        if cadence == "authentic":
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
        if cadence == "authentic":
            return "final cadence and closure"
        if cadence != "none":
            return "phrase cadence"
        if index <= 4:
            return "opening motif"
        if section == "B":
            return "contrasting motivic variation"
        if index > bars - 4:
            return "return preparation"
        return "motif repetition and development"

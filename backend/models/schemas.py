"""Dataclass schemas shared by Sera agents, generators, validators, and storage.

The runtime pipeline keeps these models dependency-light so unit tests and
training utilities can import them without requiring FastAPI.  V0.2 keeps the
old MVP field names while exposing the paper-facing Agent plan JSON contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SUPPORTED_STYLES = {
    "classical",
    "romantic",
    "jazz",
    "pop",
    "electronic",
    "chinese",
    "experimental",
    "ambient",
    "minimalist",
}
SUPPORTED_METERS = {"4/4", "3/4", "6/8"}
SUPPORTED_TEXTURES = {
    "melody_accompaniment",
    "chordal",
    "arpeggiated",
    "simple_counterpoint",
    "single_line",
}
SUPPORTED_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


AGENT_PLAN_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "title",
        "style",
        "mood",
        "instrumentation",
        "key",
        "meter",
        "tempo",
        "length_measures",
        "form",
        "texture",
        "difficulty",
        "harmony_plan",
        "section_plan",
        "revision_goals",
    ],
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "style": {"type": "string"},
        "mood": {"type": "string"},
        "instrumentation": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "key": {"type": "string"},
        "meter": {"type": "string", "enum": sorted(SUPPORTED_METERS)},
        "tempo": {"type": "integer", "minimum": 40, "maximum": 220},
        "length_measures": {"type": "integer", "enum": [8, 16, 32]},
        "form": {"type": "string"},
        "texture": {"type": "string", "enum": sorted(SUPPORTED_TEXTURES)},
        "difficulty": {"type": "string", "enum": sorted(SUPPORTED_DIFFICULTIES)},
        "harmony_plan": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "section_plan": {"type": "array", "items": {"type": "object"}, "minItems": 1},
        "revision_goals": {"type": "array", "items": {"type": "string"}},
    },
}


def validate_agent_plan_json(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate the stable V0.2 Agent plan JSON without adding jsonschema.

    TODO: Swap this small checker for full JSON Schema validation if Sera adds
    a schema dependency for model-constrained LLM calls.
    """

    errors: list[str] = []
    for key in AGENT_PLAN_JSON_SCHEMA["required"]:
        if key not in data:
            errors.append(f"missing required field: {key}")

    if not isinstance(data.get("title"), str) or not data.get("title", "").strip():
        errors.append("title must be a non-empty string")
    if not isinstance(data.get("instrumentation"), list) or not data.get("instrumentation"):
        errors.append("instrumentation must be a non-empty list")
    if data.get("meter") not in SUPPORTED_METERS:
        errors.append(f"meter must be one of {sorted(SUPPORTED_METERS)}")
    if data.get("texture") not in SUPPORTED_TEXTURES:
        errors.append(f"texture must be one of {sorted(SUPPORTED_TEXTURES)}")
    if data.get("difficulty") not in SUPPORTED_DIFFICULTIES:
        errors.append(f"difficulty must be one of {sorted(SUPPORTED_DIFFICULTIES)}")

    tempo = data.get("tempo")
    if not isinstance(tempo, int) or tempo < 40 or tempo > 220:
        errors.append("tempo must be an integer from 40 to 220")
    length = data.get("length_measures")
    if length not in {8, 16, 32}:
        errors.append("length_measures must be 8, 16, or 32")
    if not isinstance(data.get("harmony_plan"), list) or not data.get("harmony_plan"):
        errors.append("harmony_plan must be a non-empty list")
    if not isinstance(data.get("section_plan"), list) or not data.get("section_plan"):
        errors.append("section_plan must be a non-empty list")
    return not errors, errors


@dataclass(slots=True)
class StructuredMusicIntent:
    """A normalized representation of a natural-language music prompt."""

    prompt: str
    title: str = ""
    style: str = "classical"
    mood: str = "focused"
    key: str = "C major"
    time_signature: str = "4/4"
    tempo_bpm: int = 90
    bars: int = 16
    instruments: list[str] = field(default_factory=lambda: ["piano"])
    texture: str = "melody_accompaniment"
    harmony: str = "functional diatonic"
    form: str = "AABA"
    difficulty: str = "intermediate"
    harmony_plan: list[str] = field(default_factory=list)
    section_plan: list[dict[str, Any]] = field(default_factory=list)
    revision_goals: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    llm_provider: str = "mock"
    llm_model: str = "mock-rule-system"
    agent_mode: str = "mock"

    def __post_init__(self) -> None:
        """Normalize aliases and defaults used by the schema JSON."""

        self.time_signature = self.time_signature if self.time_signature in SUPPORTED_METERS else "4/4"
        self.tempo_bpm = max(40, min(220, int(self.tempo_bpm)))
        self.bars = self.bars if self.bars in {8, 16, 32} else min({8, 16, 32}, key=lambda item: abs(item - self.bars))
        self.texture = self.texture if self.texture in SUPPORTED_TEXTURES else "melody_accompaniment"
        self.difficulty = self.difficulty if self.difficulty in SUPPORTED_DIFFICULTIES else "intermediate"
        self.instruments = self.instruments or ["piano"]
        if not self.title:
            self.title = f"{self.style.title()} Sketch in {self.key}"
        if not self.harmony_plan:
            self.harmony_plan = ["i", "VI", "iv", "V"] if "minor" in self.key.lower() else ["I", "vi", "IV", "V"]
        if not self.revision_goals:
            self.revision_goals = ["valid MusicXML", "complete measures", "comfortable piano range"]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        payload = asdict(self)
        payload.update(
            {
                "instrumentation": list(self.instruments),
                "meter": self.time_signature,
                "tempo": self.tempo_bpm,
                "length_measures": self.bars,
            }
        )
        return payload

    def to_agent_plan_json(self) -> dict[str, Any]:
        """Return the stable V0.2 JSON object shown to users and papers."""

        return {
            "title": self.title,
            "style": self.style,
            "mood": self.mood,
            "instrumentation": list(self.instruments),
            "key": self.key,
            "meter": self.time_signature,
            "tempo": self.tempo_bpm,
            "length_measures": self.bars,
            "form": self.form,
            "texture": self.texture,
            "difficulty": self.difficulty,
            "harmony_plan": list(self.harmony_plan),
            "section_plan": list(self.section_plan),
            "revision_goals": list(self.revision_goals),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructuredMusicIntent":
        """Rebuild an intent from persisted experiment JSON."""

        return cls(
            prompt=str(data.get("prompt", "")),
            title=str(data.get("title", "")),
            style=str(data.get("style", "classical")),
            mood=str(data.get("mood", "focused")),
            key=str(data.get("key", "C major")),
            time_signature=str(data.get("time_signature") or data.get("meter") or "4/4"),
            tempo_bpm=int(data.get("tempo_bpm") or data.get("tempo") or 90),
            bars=int(data.get("bars") or data.get("length_measures") or 16),
            instruments=list(data.get("instruments") or data.get("instrumentation") or ["piano"]),
            texture=str(data.get("texture", "melody_accompaniment")),
            harmony=str(data.get("harmony", "functional diatonic")),
            form=str(data.get("form", "AABA")),
            difficulty=str(data.get("difficulty", "intermediate")),
            harmony_plan=list(data.get("harmony_plan") or []),
            section_plan=list(data.get("section_plan") or []),
            revision_goals=list(data.get("revision_goals") or []),
            constraints=list(data.get("constraints") or []),
            llm_provider=str(data.get("llm_provider", "mock")),
            llm_model=str(data.get("llm_model", "mock-rule-system")),
            agent_mode=str(data.get("agent_mode", "mock")),
        )


@dataclass(slots=True)
class MeasurePlan:
    """A compact measure-level plan produced by the planning agent."""

    index: int
    section: str
    chord: str
    function: str
    rhythm: str
    density: str
    cadence: str = ""
    notes: list[str] = field(default_factory=list)
    texture: str = "melody_accompaniment"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MeasurePlan":
        """Rebuild a measure plan from persisted experiment JSON."""

        return cls(
            index=int(data.get("index", 1)),
            section=str(data.get("section", "A")),
            chord=str(data.get("chord", "I")),
            function=str(data.get("function", "tonic")),
            rhythm=str(data.get("rhythm", "quarter pulse")),
            density=str(data.get("density", "medium")),
            cadence=str(data.get("cadence", "")),
            notes=list(data.get("notes") or []),
            texture=str(data.get("texture", "melody_accompaniment")),
            description=str(data.get("description", "")),
        )


@dataclass(slots=True)
class CompositionPlan:
    """A complete symbolic composition plan for one generation run."""

    intent: StructuredMusicIntent
    measures: list[MeasurePlan]
    global_plan: dict[str, Any]
    baseline: str = "rule_based_v0"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        agent_plan = self.intent.to_agent_plan_json()
        schema_valid, schema_errors = validate_agent_plan_json(agent_plan)

        return {
            "intent": self.intent.to_dict(),
            "measures": [measure.to_dict() for measure in self.measures],
            "global_plan": self.global_plan,
            "agent_plan_json": agent_plan,
            "agent_plan_schema": AGENT_PLAN_JSON_SCHEMA,
            "schema_validation": {"valid": schema_valid, "errors": schema_errors},
            "baseline": self.baseline,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompositionPlan":
        """Rebuild a composition plan from persisted experiment JSON."""

        return cls(
            intent=StructuredMusicIntent.from_dict(data.get("intent", {})),
            measures=[MeasurePlan.from_dict(item) for item in data.get("measures", [])],
            global_plan=dict(data.get("global_plan", {})),
            baseline=str(data.get("baseline", "rule_based_v0")),
        )


@dataclass(slots=True)
class ValidationResult:
    """MusicXML and theory validation summary."""

    valid: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)

    def to_report(self) -> dict[str, Any]:
        """Return the V0.2 validation_report.json shape."""

        return {
            "valid_musicxml": bool(self.metrics.get("valid_musicxml", self.metrics.get("musicxml_parseable", False))),
            "measure_count_match": bool(self.metrics.get("measure_count_match", False)),
            "bar_completeness_score": float(self.metrics.get("bar_completeness_score", self.metrics.get("bar_completeness", 0.0))),
            "pitch_range_valid": bool(self.metrics.get("pitch_range_valid", False)),
            "empty_measure_count": int(self.metrics.get("empty_measure_count", 0)),
            "midi_export_success": bool(self.metrics.get("midi_export_success", False)),
            "pdf_export_success": bool(self.metrics.get("pdf_export_success", False)),
            "warnings": list(self.warnings),
            "errors": list(self.issues),
        }


@dataclass(slots=True)
class GenerationArtifacts:
    """Paths and payloads created by the symbolic generator."""

    run_id: str
    musicxml_path: str
    midi_path: str
    abc_path: str
    pdf_path: str
    musicxml: str
    abc: str
    note_events: list[dict[str, Any]] = field(default_factory=list)
    plan_json_path: str = ""
    validation_report_path: str = ""
    experiment_dir: str = ""
    metadata_path: str = ""
    revision_history_path: str = ""
    experiment_log_path: str = ""
    export_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)


@dataclass(slots=True)
class ExperimentRecord:
    """Persisted record for paper reproducibility."""

    run_id: str
    prompt: str
    intent: dict[str, Any]
    plan: dict[str, Any]
    artifacts: dict[str, Any]
    validation: dict[str, Any]
    revision: dict[str, Any]
    evaluation: dict[str, Any]
    user_rating: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)

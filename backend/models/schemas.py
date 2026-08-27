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
    "cinematic",
    "new_age",
    "game",
    "custom",
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
    "waltz",
    "alberti",
    "bass_chord",
    "ostinato",
    "ostinato_melody",
    "chordal_arpeggiated",
    "pentatonic_open_texture",
}
SUPPORTED_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
SUPPORTED_RHYTHMIC_DENSITIES = {"low", "medium", "high"}
SUPPORTED_MELODIC_CONTOURS = {"ascending", "descending", "arch", "wave", "static"}
SUPPORTED_INTERVAL_PROFILES = {"stepwise", "mixed", "leaping"}
SUPPORTED_CADENCES = {"none", "half", "authentic"}
SUPPORTED_POLYPHONY = {"monophonic", "dyadic", "chordal"}
SUPPORTED_TENSIONS = {"low", "medium", "high"}
SUPPORTED_MOTIF_STRATEGIES = {
    "repeat",
    "sequence_up",
    "sequence_down",
    "inversion",
    "rhythmic_variation",
    "cadence",
}
V05_CONTROL_DEFAULTS = {
    "rhythmic_density": "medium",
    "melodic_contour": "wave",
    "interval_profile": "mixed",
    "cadence": "none",
    "polyphony": "monophonic",
    "tension": "medium",
    "motif_id": "A",
    "motif_strategy": "repeat",
}


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
        "musical_controls",
        "revision_goals",
    ],
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "style": {"type": "string"},
        "base_style": {"type": "string"},
        "custom_style_tags": {"type": "array", "items": {"type": "string"}},
        "style_profile": {"type": "object"},
        "run_seed": {"type": "integer"},
        "seed_source": {"type": "string"},
        "variant_id": {"type": "string"},
        "generation_nonce": {"type": "string"},
        "raw_prompt": {"type": "string"},
        "ui_controls": {"type": "object"},
        "prompt_terms": {"type": "array", "items": {"type": "object"}},
        "source_prompt_terms": {"type": "array", "items": {"type": "string"}},
        "unparsed_prompt_terms": {"type": "array", "items": {"type": "string"}},
        "prompt_ui_conflicts": {"type": "array", "items": {"type": "object"}},
        "resolved_generation_request": {"type": "object"},
        "intent_source": {"type": "string"},
        "source_control_terms": {"type": "array", "items": {"type": "object"}},
        "control_only_intent": {"type": "boolean"},
        "plan_grounding": {"type": "array", "items": {"type": "object"}},
        "prompt_plan_alignment_score": {"type": "number"},
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
        "musical_controls": {
            "type": "object",
            "properties": {
                "rhythmic_density": {"type": "string", "enum": sorted(SUPPORTED_RHYTHMIC_DENSITIES)},
                "melodic_contour": {"type": "string", "enum": sorted(SUPPORTED_MELODIC_CONTOURS)},
                "interval_profile": {"type": "string", "enum": sorted(SUPPORTED_INTERVAL_PROFILES)},
                "cadence": {"type": "string", "enum": sorted(SUPPORTED_CADENCES)},
                "polyphony": {"type": "string", "enum": sorted(SUPPORTED_POLYPHONY)},
                "tension": {"type": "string", "enum": sorted(SUPPORTED_TENSIONS)},
                "motif_id": {"type": "string"},
                "motif_strategy": {"type": "string", "enum": sorted(SUPPORTED_MOTIF_STRATEGIES)},
            },
        },
        "revision_goals": {"type": "array", "items": {"type": "string"}},
    },
}


def normalize_agent_plan_json(data: dict[str, Any]) -> dict[str, Any]:
    """Fill V0.5 control defaults before lightweight schema validation."""

    normalized = dict(data)
    controls = dict(normalized.get("musical_controls") or {})
    for key, value in V05_CONTROL_DEFAULTS.items():
        controls.setdefault(key, value)
    controls["rhythmic_density"] = _safe_choice(
        controls.get("rhythmic_density"), SUPPORTED_RHYTHMIC_DENSITIES, "medium"
    )
    controls["melodic_contour"] = _safe_choice(
        controls.get("melodic_contour"), SUPPORTED_MELODIC_CONTOURS, "wave"
    )
    controls["interval_profile"] = _safe_choice(
        controls.get("interval_profile"), SUPPORTED_INTERVAL_PROFILES, "mixed"
    )
    controls["cadence"] = _safe_choice(controls.get("cadence"), SUPPORTED_CADENCES, "none")
    controls["polyphony"] = _safe_choice(controls.get("polyphony"), SUPPORTED_POLYPHONY, "monophonic")
    controls["tension"] = _safe_choice(controls.get("tension"), SUPPORTED_TENSIONS, "medium")
    controls["motif_strategy"] = _safe_choice(
        controls.get("motif_strategy"), SUPPORTED_MOTIF_STRATEGIES, "repeat"
    )
    controls["motif_id"] = str(controls.get("motif_id") or "A")[:32]
    normalized["musical_controls"] = controls

    section_plan = []
    for item in normalized.get("section_plan") or []:
        section = dict(item)
        section.setdefault("rhythmic_density", controls["rhythmic_density"])
        section.setdefault("melodic_contour", controls["melodic_contour"])
        section.setdefault("cadence", controls["cadence"])
        section.setdefault("motif_strategy", controls["motif_strategy"])
        section_plan.append(section)
    normalized["section_plan"] = section_plan
    return normalized


def validate_agent_plan_json(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate the stable V0.2 Agent plan JSON without adding jsonschema.

    TODO: Swap this small checker for full JSON Schema validation if Sera adds
    a schema dependency for model-constrained LLM calls.
    """

    data = normalize_agent_plan_json(data)
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
    controls = data.get("musical_controls") or {}
    if controls.get("rhythmic_density") not in SUPPORTED_RHYTHMIC_DENSITIES:
        errors.append(f"rhythmic_density must be one of {sorted(SUPPORTED_RHYTHMIC_DENSITIES)}")
    if controls.get("melodic_contour") not in SUPPORTED_MELODIC_CONTOURS:
        errors.append(f"melodic_contour must be one of {sorted(SUPPORTED_MELODIC_CONTOURS)}")
    if controls.get("cadence") not in SUPPORTED_CADENCES:
        errors.append(f"cadence must be one of {sorted(SUPPORTED_CADENCES)}")
    return not errors, errors


def _safe_choice(value: Any, allowed: set[str], fallback: str) -> str:
    clean = str(value or fallback).replace("-", "_").replace(" ", "_").lower()
    return clean if clean in allowed else fallback


@dataclass(slots=True)
class StructuredMusicIntent:
    """A normalized representation of a natural-language music prompt."""

    prompt: str
    title: str = ""
    style: str = "classical"
    base_style: str = ""
    custom_style_tags: list[str] = field(default_factory=list)
    style_profile: dict[str, Any] = field(default_factory=dict)
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
    rhythmic_density: str = "medium"
    melodic_contour: str = "wave"
    interval_profile: str = "mixed"
    cadence: str = "none"
    polyphony: str = "monophonic"
    tension: str = "medium"
    motif_id: str = "A"
    motif_strategy: str = "repeat"
    llm_provider: str = "mock"
    llm_model: str = "mock-rule-system"
    agent_mode: str = "mock"
    raw_prompt: str = ""
    ui_controls: dict[str, Any] = field(default_factory=dict)
    prompt_terms: list[dict[str, Any]] = field(default_factory=list)
    source_prompt_terms: list[str] = field(default_factory=list)
    unparsed_prompt_terms: list[str] = field(default_factory=list)
    prompt_ui_conflicts: list[dict[str, Any]] = field(default_factory=list)
    resolved_generation_request: dict[str, Any] = field(default_factory=dict)
    intent_source: str = "raw_prompt"
    source_control_terms: list[dict[str, Any]] = field(default_factory=list)
    control_only_intent: bool = False
    plan_grounding: list[dict[str, Any]] = field(default_factory=list)
    prompt_plan_alignment_score: float = 0.0
    run_seed: int = 0
    seed_source: str = ""
    variant_id: str = ""
    generation_nonce: str = ""

    def __post_init__(self) -> None:
        """Normalize aliases and defaults used by the schema JSON."""

        self.time_signature = self.time_signature if self.time_signature in SUPPORTED_METERS else "4/4"
        self.tempo_bpm = max(40, min(220, int(self.tempo_bpm)))
        self.bars = self.bars if self.bars in {8, 16, 32} else min({8, 16, 32}, key=lambda item: abs(item - self.bars))
        self.texture = self.texture if self.texture in SUPPORTED_TEXTURES else "melody_accompaniment"
        self.difficulty = self.difficulty if self.difficulty in SUPPORTED_DIFFICULTIES else "intermediate"
        self.rhythmic_density = _safe_choice(self.rhythmic_density, SUPPORTED_RHYTHMIC_DENSITIES, "medium")
        self.melodic_contour = _safe_choice(self.melodic_contour, SUPPORTED_MELODIC_CONTOURS, "wave")
        self.interval_profile = _safe_choice(self.interval_profile, SUPPORTED_INTERVAL_PROFILES, "mixed")
        self.cadence = _safe_choice(self.cadence, SUPPORTED_CADENCES, "none")
        self.polyphony = _safe_choice(self.polyphony, SUPPORTED_POLYPHONY, "monophonic")
        self.tension = _safe_choice(self.tension, SUPPORTED_TENSIONS, "medium")
        self.motif_strategy = _safe_choice(self.motif_strategy, SUPPORTED_MOTIF_STRATEGIES, "repeat")
        self.motif_id = str(self.motif_id or "A")[:32]
        self.base_style = str(self.base_style or (self.style_profile or {}).get("base_style") or self.style or "classical")
        self.custom_style_tags = [str(item)[:40] for item in (self.custom_style_tags or []) if str(item).strip()][:12]
        self.style_profile = dict(self.style_profile or {})
        if self.custom_style_tags:
            self.style_profile.setdefault("custom_style_tags", list(self.custom_style_tags))
            self.style_profile.setdefault("base_style", self.base_style)
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

        return normalize_agent_plan_json({
            "title": self.title,
            "style": self.style,
            "base_style": self.base_style,
            "custom_style_tags": list(self.custom_style_tags),
            "style_profile": dict(self.style_profile),
            "run_seed": int(self.run_seed or 0),
            "seed_source": self.seed_source,
            "variant_id": self.variant_id,
            "generation_nonce": self.generation_nonce,
            "raw_prompt": self.raw_prompt or self.prompt,
            "ui_controls": dict(self.ui_controls),
            "prompt_terms": list(self.prompt_terms),
            "source_prompt_terms": list(self.source_prompt_terms),
            "unparsed_prompt_terms": list(self.unparsed_prompt_terms),
            "prompt_ui_conflicts": list(self.prompt_ui_conflicts),
            "resolved_generation_request": dict(self.resolved_generation_request),
            "intent_source": self.intent_source,
            "source_control_terms": list(self.source_control_terms),
            "control_only_intent": bool(self.control_only_intent),
            "plan_grounding": list(self.plan_grounding),
            "prompt_plan_alignment_score": float(self.prompt_plan_alignment_score),
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
            "musical_controls": {
                "rhythmic_density": self.rhythmic_density,
                "melodic_contour": self.melodic_contour,
                "interval_profile": self.interval_profile,
                "cadence": self.cadence,
                "polyphony": self.polyphony,
                "tension": self.tension,
                "motif_id": self.motif_id,
                "motif_strategy": self.motif_strategy,
            },
            "revision_goals": list(self.revision_goals),
        })

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructuredMusicIntent":
        """Rebuild an intent from persisted experiment JSON."""

        return cls(
            prompt=str(data.get("prompt", "")),
            title=str(data.get("title", "")),
            style=str(data.get("style", "classical")),
            base_style=str(data.get("base_style", "")),
            custom_style_tags=list(data.get("custom_style_tags") or []),
            style_profile=dict(data.get("style_profile") or {}),
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
            rhythmic_density=str(data.get("rhythmic_density", "medium")),
            melodic_contour=str(data.get("melodic_contour", "wave")),
            interval_profile=str(data.get("interval_profile", "mixed")),
            cadence=str(data.get("cadence", "none")),
            polyphony=str(data.get("polyphony", "monophonic")),
            tension=str(data.get("tension", "medium")),
            motif_id=str(data.get("motif_id", "A")),
            motif_strategy=str(data.get("motif_strategy", "repeat")),
            llm_provider=str(data.get("llm_provider", "mock")),
            llm_model=str(data.get("llm_model", "mock-rule-system")),
            agent_mode=str(data.get("agent_mode", "mock")),
            raw_prompt=str(data.get("raw_prompt", data.get("prompt", ""))),
            ui_controls=dict(data.get("ui_controls") or {}),
            prompt_terms=list(data.get("prompt_terms") or []),
            source_prompt_terms=list(data.get("source_prompt_terms") or []),
            unparsed_prompt_terms=list(data.get("unparsed_prompt_terms") or []),
            prompt_ui_conflicts=list(data.get("prompt_ui_conflicts") or []),
            resolved_generation_request=dict(data.get("resolved_generation_request") or {}),
            intent_source=str(data.get("intent_source", "raw_prompt")),
            source_control_terms=list(data.get("source_control_terms") or []),
            control_only_intent=bool(data.get("control_only_intent", False)),
            plan_grounding=list(data.get("plan_grounding") or []),
            prompt_plan_alignment_score=float(data.get("prompt_plan_alignment_score") or 0.0),
            run_seed=int(data.get("run_seed") or 0),
            seed_source=str(data.get("seed_source", "")),
            variant_id=str(data.get("variant_id", "")),
            generation_nonce=str(data.get("generation_nonce", "")),
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
    cadence: str = "none"
    rhythmic_density: str = "medium"
    melodic_contour: str = "wave"
    interval_profile: str = "mixed"
    polyphony: str = "monophonic"
    tension: str = "medium"
    motif_id: str = "A"
    motif_strategy: str = "repeat"
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
            cadence=str(data.get("cadence", "none") or "none").replace(" cadence", ""),
            rhythmic_density=str(data.get("rhythmic_density") or data.get("density") or "medium"),
            melodic_contour=str(data.get("melodic_contour", "wave")),
            interval_profile=str(data.get("interval_profile", "mixed")),
            polyphony=str(data.get("polyphony", "monophonic")),
            tension=str(data.get("tension", "medium")),
            motif_id=str(data.get("motif_id", "A")),
            motif_strategy=str(data.get("motif_strategy", "repeat")),
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

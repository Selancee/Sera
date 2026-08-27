"""Motif memory and development helpers for V0.96.2 phrase melody generation."""

from __future__ import annotations

from typing import Any


DEFAULT_SCALE = [0, 2, 4, 5, 7, 9, 11]
PENTATONIC_SCALE = [0, 2, 4, 7, 9]
MINOR_MODAL_SCALE = [0, 2, 3, 5, 7, 8, 10]


def create_motif_memory(seed_motif: list[int], style_profile: dict[str, Any]) -> dict[str, Any]:
    """Create a small mutable memory object for phrase-level motif reuse."""

    motif = [int(item) for item in (seed_motif or [0, 2, 4, 7])]
    style = _style_family(style_profile)
    memory = {
        "engine": "motif_memory_v0962",
        "style_family": style,
        "primary_motif": motif,
        "motifs": {
            "primary": {
                "motif_id": "primary",
                "motif": motif,
                "role": "opening",
                "metadata": {"source": "seed"},
            }
        },
        "uses": [],
    }
    return memory


def remember_motif(memory: dict[str, Any], motif_id: str, motif: list[int], metadata: dict[str, Any]) -> dict[str, Any]:
    """Store or replace a motif in memory."""

    memory = dict(memory or {})
    memory.setdefault("motifs", {})
    memory.setdefault("uses", [])
    clean_id = str(motif_id or f"motif_{len(memory['motifs']) + 1}")
    memory["motifs"][clean_id] = {
        "motif_id": clean_id,
        "motif": [int(item) for item in motif],
        "role": str((metadata or {}).get("role") or ""),
        "metadata": dict(metadata or {}),
    }
    if clean_id == "primary" or not memory.get("primary_motif"):
        memory["primary_motif"] = [int(item) for item in motif]
    return memory


def retrieve_motif(memory: dict[str, Any], role: str, rng: Any) -> dict[str, Any]:
    """Return the best available motif for a phrase role."""

    motifs = dict((memory or {}).get("motifs") or {})
    role = str(role or "")
    if role in {"consequent", "return", "cadence", "final"} and "primary" in motifs:
        return dict(motifs["primary"])
    role_matches = [item for item in motifs.values() if str(item.get("role")) == role]
    if role_matches:
        return dict(_choice(rng, role_matches))
    if motifs:
        return dict(motifs.get("primary") or next(iter(motifs.values())))
    return {"motif_id": "primary", "motif": [0, 2, 4, 7], "role": "opening", "metadata": {}}


def develop_motif(motif: list[int], strategy: str, style_profile: dict[str, Any], rng: Any) -> list[int]:
    """Develop a semitone-offset motif with conservative musical transforms."""

    source = [int(item) for item in (motif or [0, 2, 4, 7])]
    if not source:
        return [0, 2, 4, 7]
    strategy = str(strategy or "repeat")
    scale = _scale_for_style(style_profile)
    if strategy == "repeat":
        return list(source)
    if strategy == "sequence_up":
        return [_shift_scale_degree(item, 1, scale) for item in source]
    if strategy == "sequence_down":
        return [_shift_scale_degree(item, -1, scale) for item in source]
    if strategy == "rhythmic_variation":
        return source[1:] + source[:1] if len(source) > 2 else list(reversed(source))
    if strategy == "interval_expansion":
        first = source[0]
        return [first + int(round((item - first) * 1.25)) for item in source]
    if strategy == "interval_contraction":
        first = source[0]
        return [first + int(round((item - first) * 0.65)) for item in source]
    if strategy == "inversion_lite":
        pivot = source[0]
        return [pivot - (item - pivot) for item in source]
    if strategy == "fragmentation":
        fragment = source[: max(2, min(3, len(source)))]
        return fragment + [_choice(rng, fragment)]
    if strategy == "answer_phrase":
        answered = list(reversed(source))
        return [_shift_scale_degree(item, -1 if index % 2 else 0, scale) for index, item in enumerate(answered)]
    if strategy == "cadential_variant":
        cadence = [7, 5, 2, 0]
        return (source[: max(1, len(source) - len(cadence))] + cadence)[: len(source)]
    if strategy == "style_colored_variant":
        return _style_colored_variant(source, style_profile, rng)
    return list(source)


def summarize_motif_memory(memory: dict[str, Any], measure_motifs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a compact V0.96.2 motif recurrence report."""

    primary = [int(item) for item in (memory or {}).get("primary_motif", [])]
    exact = 0
    developed = 0
    variations: list[str] = []
    for item in measure_motifs:
        motif = [int(value) for value in item.get("motif", [])]
        strategy = str(item.get("motif_transform") or "")
        if motif[: len(primary)] == primary[: len(motif)]:
            exact += 1
        elif _motif_identity(primary, motif) >= 0.45:
            developed += 1
        if strategy and strategy not in variations:
            variations.append(strategy)
    total = max(1, len(measure_motifs))
    exact_rate = exact / total
    identity = max([_motif_identity(primary, [int(value) for value in item.get("motif", [])]) for item in measure_motifs] or [0.0])
    return {
        "engine": "motif_memory_v0962",
        "primary_motif": primary,
        "motif_recurrence_count": exact + developed,
        "motif_variation_types": variations,
        "exact_repetition_count": exact,
        "developed_repetition_count": developed,
        "motif_identity_score": round(identity, 4),
        "mechanical_repetition_penalty": round(max(0.0, exact_rate - 0.35), 4),
    }


def _style_colored_variant(source: list[int], style_profile: dict[str, Any], rng: Any) -> list[int]:
    family = _style_family(style_profile)
    if family == "jazz" and len(source) >= 3:
        return [source[0], source[1] - 1, source[2], source[-1] + 1]
    if family == "chinese":
        scale = PENTATONIC_SCALE
        return [_nearest_scale(item, scale) for item in source]
    if family == "cyberpunk":
        return [source[index] + (-1 if index % 3 == 1 else 0) for index in range(len(source))]
    if family == "romantic" and len(source) >= 4:
        return [source[0], source[1], source[2] + 2, source[3]]
    if family == "pop" and len(source) >= 3:
        return [source[0], source[1], source[2], source[1]]
    return source[1:] + source[:1] if len(source) > 1 else source


def _motif_identity(primary: list[int], motif: list[int]) -> float:
    if not primary or not motif:
        return 0.0
    intervals_a = _intervals(primary)
    intervals_b = _intervals(motif)
    if not intervals_a or not intervals_b:
        return 1.0 if primary[0] == motif[0] else 0.0
    span = min(len(intervals_a), len(intervals_b))
    matches = 0
    for index in range(span):
        if abs(intervals_a[index] - intervals_b[index]) <= 2:
            matches += 1
    return matches / max(1, span)


def _intervals(values: list[int]) -> list[int]:
    return [values[index + 1] - values[index] for index in range(len(values) - 1)]


def _shift_scale_degree(value: int, delta: int, scale: list[int]) -> int:
    octave = int(value // 12)
    pc = int(value % 12)
    nearest = min(scale, key=lambda item: abs(item - pc))
    position = scale.index(nearest)
    shifted = scale[(position + delta) % len(scale)]
    octave_adjust = 12 if position + delta >= len(scale) else -12 if position + delta < 0 else 0
    return octave * 12 + shifted + octave_adjust


def _nearest_scale(value: int, scale: list[int]) -> int:
    octave = int(value // 12)
    pc = int(value % 12)
    nearest = min(scale, key=lambda item: min(abs(item - pc), 12 - abs(item - pc)))
    return octave * 12 + nearest


def _scale_for_style(style_profile: dict[str, Any]) -> list[int]:
    family = _style_family(style_profile)
    if family == "chinese":
        return PENTATONIC_SCALE
    if family == "cyberpunk":
        return MINOR_MODAL_SCALE
    return DEFAULT_SCALE


def _style_family(style_profile: dict[str, Any]) -> str:
    profile = style_profile or {}
    tags = {str(item).lower() for item in profile.get("custom_style_tags", [])}
    family = str(profile.get("style_family") or profile.get("base_style") or profile.get("style") or "classical").lower()
    if "cyberpunk" in tags or family == "electronic":
        return "cyberpunk"
    if "chinese" in tags:
        return "chinese"
    return family


def _choice(rng: Any, values: list[Any]) -> Any:
    if not values:
        return None
    if hasattr(rng, "choice"):
        return rng.choice(values)
    return values[0]

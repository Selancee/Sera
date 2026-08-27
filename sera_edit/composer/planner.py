"""LLM-assisted composition planning with server-owned musical constraints."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from backend.services.score_document_service import normalize_score_document
from sera_edit.composer.models import CompositionMode, CompositionPlan, StyleFamily
from sera_edit.composer.style_knowledge import default_style_knowledge_base, retrieve_style_knowledge
from sera_edit.composer.theory_knowledge import retrieve_theory
from sera_edit.composer.texture_analysis import analyze_texture
from sera_edit.domain.fingerprints import score_fingerprint
from sera_edit.domain.score_scope import ScoreScope
from sera_edit.providers.base import LLMProvider, ProviderResponse


PROMPT_VERSION = "sera_composition_plan_v4.1"
ALLOWED_MODES = {"theory_variation", "reharmonize", "orchestration_advice"}
ALLOWED_STYLES = {"classical", "romantic", "jazz", "pop", "minimal", "modal", "cinematic"}
ALLOWED_TEXTURES = {"melody_accompaniment", "contrapuntal", "chordal", "arpeggiated", "sparse", "layered"}
ALLOWED_MOTIF_STRATEGIES = {"preserve_contour", "sequence", "inversion_hint", "rhythmic_identity", "call_response"}
ALLOWED_DYNAMICS = {"pp", "p", "mp", "mf", "f", "ff"}
ROMAN_PATTERN = re.compile(r"^(?:b|#)?(?:I|II|III|IV|V|VI|VII|i|ii|iii|iv|v|vi|vii)(?:o|°|7)?$")


def composition_plan_schema() -> dict[str, Any]:
    """Return the narrow transport schema accepted from a general LLM."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "mode",
            "style_family",
            "harmonic_progression",
            "texture",
            "motif_strategy",
            "tension_curve",
            "dynamics_curve",
            "preserve_melody",
            "orchestration_notes",
        ],
        "properties": {
            "mode": {"type": "string", "enum": sorted(ALLOWED_MODES)},
            "style_family": {"type": "string", "enum": sorted(ALLOWED_STYLES)},
            "harmonic_progression": {"type": "array", "minItems": 1, "maxItems": 8, "items": {"type": "string"}},
            "texture": {"type": "string", "enum": sorted(ALLOWED_TEXTURES)},
            "motif_strategy": {"type": "string", "enum": sorted(ALLOWED_MOTIF_STRATEGIES)},
            "tension_curve": {"type": "array", "minItems": 1, "maxItems": 8, "items": {"type": "number", "minimum": 0, "maximum": 1}},
            "dynamics_curve": {"type": "array", "minItems": 1, "maxItems": 8, "items": {"type": "string", "enum": sorted(ALLOWED_DYNAMICS)}},
            "preserve_melody": {"type": "boolean"},
            "orchestration_notes": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 240}},
        },
    }


def infer_mode_and_style(brief: str) -> tuple[CompositionMode, StyleFamily]:
    """Infer a conservative local default from Chinese or English wording."""

    text = brief.lower()
    if any(token in text for token in ("配器", "orchestrat", "instrumentation", "乐器分配")):
        mode: CompositionMode = "orchestration_advice"
    # "保持节奏和声部数量不变" contains the character sequence "和声部",
    # but it is a conjunction plus "voice count", not a harmony request.
    # Keep the Chinese boundary explicit so melody rewrites are not converted
    # into a preserve-melody reharmonization with nothing legal to edit.
    elif re.search(r"(?:重新和声化|重配和声|改写和声|和声(?!部)|和弦|reharm|\bharmony\b)", text):
        mode = "reharmonize"
    else:
        mode = "theory_variation"
    style = default_style_knowledge_base().resolve_style(text, "classical")
    return mode, style


def plan_composition(
    score_document: dict[str, Any],
    brief: str,
    target_scope_payload: dict[str, Any],
    protected_scope_payload: dict[str, Any] | None = None,
    *,
    seed: int = 42,
    provider: LLMProvider | None = None,
    max_tokens: int = 1800,
) -> tuple[CompositionPlan, list[dict[str, object]], dict[str, Any]]:
    """Create a canonical plan, using the LLM only for high-level choices."""

    score = normalize_score_document(score_document)
    target_scope = ScoreScope.from_dict(target_scope_payload)
    protected_scope = ScoreScope.from_dict(protected_scope_payload)
    selected = target_scope.select(score)
    measures = sorted({context.measure for context in selected} or set(target_scope.measures))
    if target_scope.empty or not measures:
        raise ValueError("请先在宿主乐谱中选择至少一个小节或音符。")
    if len(measures) > 8:
        raise ValueError("Composer V0.1 每次最多处理 8 个小节，请缩小宿主选区。")
    inferred_mode, inferred_style = infer_mode_and_style(brief)
    initial_style_knowledge = retrieve_style_knowledge(
        brief,
        inferred_style,
        inferred_mode,
        score_document=score,
        target_scope=target_scope.as_dict(),
    )
    source_texture = analyze_texture(score, target_scope.as_dict())
    theory = retrieve_theory(brief, inferred_mode, inferred_style)
    proposal: dict[str, Any] | None = None
    response: ProviderResponse | None = None
    fallback_reason = ""
    if provider is not None:
        payload = {
            "brief": brief.strip(),
            "immutable_score_context": _composer_score_summary(score, selected, measures),
            "measure_count": len(measures),
            "source_texture_analysis": {
                "texture": source_texture["texture"],
                "confidence": source_texture["confidence"],
                "voice_count": source_texture["voice_count"],
                "attack_alignment_ratio": source_texture["attack_alignment_ratio"],
                "rhythmic_independence": source_texture["rhythmic_independence"],
                "primary_voice_id": source_texture["primary_voice_id"],
            },
            "inferred_mode": inferred_mode,
                "inferred_style": inferred_style,
                "theory_principles": theory,
                "retrieved_knowledge_context": {
                    "knowledge_base_id": initial_style_knowledge["knowledge_base_id"],
                    "schema_version": initial_style_knowledge["schema_version"],
                    "style_id": initial_style_knowledge["style_id"],
                    "query": initial_style_knowledge["query"],
                    "retrieval": initial_style_knowledge["retrieval"],
                    "selected_rules": initial_style_knowledge["matched_rules"],
                },
            "hard_constraints": {
                "preserve_rhythm": True,
                "preserve_event_count": True,
                "preserve_instrumentation": True,
                "do_not_choose_event_pitches": True,
                "do_not_widen_scope": True,
            },
        }
        try:
            response = provider.generate(
                [
                    {
                        "role": "system",
                        "content": (
                            "You plan a short symbolic-music transformation for Sera. Return one valid JSON object only. "
                            "Choose phrase, harmony, texture, motif, tension, and dynamics, but never output notes, event IDs, "
                            "MusicXML, or structural changes. Use only the small retrieved rule context supplied by the server. "
                            "The server owns all immutable score facts and safety constraints. Example JSON output: "
                            '{"mode":"theory_variation","style_family":"classical","harmonic_progression":["I","V"],'
                            '"texture":"melody_accompaniment","motif_strategy":"preserve_contour",'
                            '"tension_curve":[0.25,0.6],"dynamics_curve":["mp","mf"],'
                            '"preserve_melody":false,"orchestration_notes":[]}'
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
                ],
                response_schema=composition_plan_schema(),
                temperature=0.0,
                seed=seed,
                max_tokens=max_tokens,
                metadata={
                    "prompt_version": PROMPT_VERSION,
                    "purpose": "composition_plan",
                    "thinking": "disabled",
                },
            )
            if isinstance(response.parsed_output, dict):
                proposal = dict(response.parsed_output)
            else:
                fallback_reason = "LLM 未返回可解析的 CompositionPlan JSON。"
        except Exception as exc:  # noqa: BLE001 - providers expose heterogeneous transport errors.
            fallback_reason = f"LLM 规划失败，已使用确定性理论计划：{exc}"
    else:
        fallback_reason = "未配置实时 LLM，已使用确定性理论计划。"
    canonical = _canonical_plan_values(
        proposal,
        inferred_mode,
        inferred_style,
        len(measures),
        seed,
        initial_style_knowledge["profile"],
    )
    final_style_knowledge = retrieve_style_knowledge(
        brief,
        canonical["style_family"],
        canonical["mode"],
        score_document=score,
        target_scope=target_scope.as_dict(),
    )
    if canonical["style_family"] != initial_style_knowledge["style_id"]:
        canonical = _canonical_plan_values(
            proposal,
            inferred_mode,
            inferred_style,
            len(measures),
            seed,
            final_style_knowledge["profile"],
        )
    theory = retrieve_theory(brief, canonical["mode"], canonical["style_family"])
    claim_ids = tuple(str(item["claim_id"]) for item in theory)
    style_rule_ids = tuple(str(item["rule_id"]) for item in final_style_knowledge["matched_rules"])
    fingerprint = score_fingerprint(score)
    identity = json.dumps(
        {"fingerprint": fingerprint, "brief": brief.strip(), "measures": measures, "seed": seed, **canonical},
        ensure_ascii=False,
        sort_keys=True,
    )
    plan = CompositionPlan(
        schema_version="1.0.0",
        plan_id=f"composition_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}",
        brief=brief.strip(),
        key=str((score.get("global") or {}).get("key", "C major")),
        meter=str((score.get("global") or {}).get("meter", "4/4")),
        measures=tuple(measures),
        theory_claim_ids=claim_ids,
        style_rule_ids=style_rule_ids,
        style_knowledge_version=str(final_style_knowledge["schema_version"]),
        knowledge_context_fingerprint=str(final_style_knowledge["query_fingerprint"]),
        knowledge_token_estimate=int(final_style_knowledge["retrieval"]["estimated_tokens"]),
        source_fingerprint=fingerprint,
        target_scope=target_scope.as_dict(),
        protected_scope=protected_scope.as_dict(),
        seed=seed,
        **canonical,
    )
    evidence = {
        "planner": "live_llm" if response is not None and proposal is not None else "deterministic_theory",
        "prompt_version": PROMPT_VERSION,
        "fallback_reason": fallback_reason,
        "provider": response.provider if response else "local_rule",
        "model": response.model if response else "sera_composer_rules_v1",
        "latency_ms": round(response.latency_ms, 3) if response else 0.0,
        "input_tokens": response.input_tokens if response else None,
        "output_tokens": response.output_tokens if response else None,
        "request_id": response.request_id if response else None,
        "style_knowledge_id": final_style_knowledge["knowledge_base_id"],
        "style_knowledge_version": final_style_knowledge["schema_version"],
        "style_knowledge_fingerprint": final_style_knowledge["fingerprint"],
        "knowledge_query_fingerprint": final_style_knowledge["query_fingerprint"],
        "knowledge_selected_cards": final_style_knowledge["retrieval"]["selected_cards"],
        "knowledge_estimated_tokens": final_style_knowledge["retrieval"]["estimated_tokens"],
        "knowledge_token_budget": final_style_knowledge["retrieval"]["token_budget"],
        "full_corpus_sent_to_llm": False,
        "source_texture": source_texture["texture"],
        "source_texture_confidence": source_texture["confidence"],
    }
    return plan, theory, evidence


def _composer_score_summary(
    score: dict[str, Any],
    selected: list[Any],
    measures: list[int],
) -> dict[str, Any]:
    """Describe the selected scaffold without sending every event to a high-level planner."""

    note_contexts = [context for context in selected if context.event.get("type") == "note"]
    voices = sorted({f"{context.staff}:v{context.voice}" for context in note_contexts})
    instruments = sorted(
        {
            str(track.get("instrument") or "").strip()
            for track in score.get("tracks") or []
            if str(track.get("instrument") or "").strip()
        }
    )
    return {
        "score_id": str(score.get("score_id") or ""),
        "source_fingerprint": score_fingerprint(score),
        "global": {
            "key": str((score.get("global") or {}).get("key") or ""),
            "meter": str((score.get("global") or {}).get("meter") or ""),
            "tempo": (score.get("global") or {}).get("tempo"),
        },
        "target_measures": list(measures),
        "selected_event_count": len(selected),
        "selected_note_count": len(note_contexts),
        "voice_count": len(voices),
        "voices": voices,
        "instruments": instruments,
    }


def _canonical_plan_values(
    proposal: dict[str, Any] | None,
    inferred_mode: CompositionMode,
    inferred_style: StyleFamily,
    measure_count: int,
    seed: int,
    style_profile: dict[str, Any],
) -> dict[str, Any]:
    raw = proposal or {}
    # The instruction classifier, not the external model, owns the operation
    # family.  Otherwise a melody-rewrite request can be reclassified as
    # "reharmonize + preserve melody", leaving no legal event to edit.
    mode: CompositionMode = inferred_mode
    style: StyleFamily = str(raw.get("style_family")) if raw.get("style_family") in ALLOWED_STYLES else inferred_style  # type: ignore[assignment]
    source_progression = raw.get("harmonic_progression")
    progression = [str(item) for item in source_progression] if isinstance(source_progression, list) else []
    if not progression or any(not ROMAN_PATTERN.fullmatch(item) for item in progression):
        planning = style_profile.get("planning") or {}
        options = planning.get("progressions") or [["I", "IV", "V", "I"]]
        progression = list(options[seed % len(options)])
    progression = _fit(progression, measure_count)
    texture = str(raw.get("texture", ""))
    if texture not in ALLOWED_TEXTURES:
        preferred_textures = list((style_profile.get("planning") or {}).get("textures") or [])
        texture = next((item for item in preferred_textures if item in ALLOWED_TEXTURES), "melody_accompaniment")
    motif = str(raw.get("motif_strategy", ""))
    if motif not in ALLOWED_MOTIF_STRATEGIES:
        preferred_motifs = list((style_profile.get("planning") or {}).get("motif_strategies") or [])
        motif = next((item for item in preferred_motifs if item in ALLOWED_MOTIF_STRATEGIES), "preserve_contour")
    tension = _numeric_curve(raw.get("tension_curve"), measure_count)
    if not tension:
        base = list((style_profile.get("planning") or {}).get("tension_curve") or [0.25, 0.38, 0.52, 0.68, 0.46, 0.72, 0.82, 0.22])
        tension = _fit(base, measure_count)
    dynamics = [str(item) for item in raw.get("dynamics_curve", [])] if isinstance(raw.get("dynamics_curve"), list) else []
    if not dynamics or any(item not in ALLOWED_DYNAMICS for item in dynamics):
        preferred_dynamics = list((style_profile.get("planning") or {}).get("dynamics_curve") or ["mp", "mf", "f", "mp"])
        dynamics = _fit(preferred_dynamics, measure_count)
    notes = raw.get("orchestration_notes")
    orchestration_notes = tuple(str(item)[:240] for item in notes[:8]) if isinstance(notes, list) else ()
    if mode == "orchestration_advice" and not orchestration_notes:
        orchestration_notes = (
            "保留宿主乐器编制；将旋律角色置于清晰中高音区。",
            "用较低密度的中低音声部承担和声支撑，避免遮蔽旋律。",
            "先在宿主软件内确认换乐器与移调规则，再执行结构性配器。",
        )
    return {
        "mode": mode,
        "style_family": style,
        "harmonic_progression": tuple(progression),
        "texture": texture,
        "motif_strategy": motif,
        "tension_curve": tuple(float(value) for value in tension),
        "dynamics_curve": tuple(dynamics),
        "preserve_rhythm": True,
        "preserve_event_count": True,
        "preserve_instrumentation": True,
        "preserve_melody": mode == "reharmonize",
        "orchestration_notes": orchestration_notes,
    }


def _fit(values: list[Any], length: int) -> list[Any]:
    result = list(values)
    while len(result) < length:
        result.extend(values)
    return result[:length]


def _numeric_curve(value: object, length: int) -> list[float]:
    if not isinstance(value, list) or not value:
        return []
    try:
        curve = [max(0.0, min(1.0, float(item))) for item in value]
    except (TypeError, ValueError):
        return []
    return _fit(curve, length)

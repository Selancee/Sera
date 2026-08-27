"""Plan grounding diagnostics for prompt-to-plan observability."""

from __future__ import annotations

from typing import Any


class PlanGroundingService:
    """Explain which prompt/control source drove important plan decisions."""

    def build(self, intent: Any, measures: list[Any] | None = None) -> dict[str, Any]:
        terms = list(getattr(intent, "prompt_terms", []) or [])
        source_terms = list(getattr(intent, "source_prompt_terms", []) or [])
        control_terms = list(getattr(intent, "source_control_terms", []) or [])
        style_profile = dict(getattr(intent, "style_profile", {}) or {})
        resolved = dict(getattr(intent, "resolved_generation_request", {}) or {})
        conflicts = list(getattr(intent, "prompt_ui_conflicts", []) or [])
        groundings: list[dict[str, Any]] = []

        def add(decision: str, source: str, field: str, confidence: float = 0.85) -> None:
            matched = _terms_for_field(terms, field) or source_terms[:4]
            if not matched and control_terms:
                matched = [str(item.get("term", "")) for item in control_terms if item.get("field") == field or field in str(item.get("field", ""))][:4]
            groundings.append(
                {
                    "decision": decision,
                    "source": source,
                    "source_prompt_terms": matched,
                    "confidence": round(confidence, 3),
                }
            )

        style_source = "style_profile_mapper" if style_profile else "default_fallback"
        add(f"style={getattr(intent, 'style', 'classical')}", style_source, "style", 0.95 if style_profile else 0.55)
        add(f"texture={getattr(intent, 'texture', '')}", style_source if style_profile.get("texture") else "explicit_ui_or_default", "texture")
        add(f"rhythmic_density={getattr(intent, 'rhythmic_density', '')}", style_source if style_profile.get("rhythmic_density") else "explicit_ui_or_default", "rhythm")
        add(f"key={getattr(intent, 'key', '')}", "raw_prompt" if _terms_for_field(terms, "key") else "default_fallback", "key")
        add(f"meter={getattr(intent, 'time_signature', '')}", "raw_prompt" if _terms_for_field(terms, "meter") else "explicit_ui_or_default", "meter")
        add(f"length_measures={getattr(intent, 'bars', '')}", "raw_prompt" if _terms_for_field(terms, "length") else "explicit_ui_or_default", "length")
        if style_profile.get("accompaniment_style"):
            add(f"accompaniment_style={style_profile['accompaniment_style']}", style_source, "accompaniment", 0.92)
        if style_profile.get("harmony_flavor"):
            add(f"harmony_flavor={style_profile['harmony_flavor']}", style_source, "style", 0.9)

        measure_count = len(measures or [])
        aligned = sum(1 for item in groundings if item["source_prompt_terms"] or item["source"] != "default_fallback")
        conflict_penalty = min(0.2, len(conflicts) * 0.04)
        alignment_score = max(0.0, min(1.0, (aligned / max(1, len(groundings))) - conflict_penalty))

        return {
            "source_prompt_terms": source_terms,
            "source_control_terms": control_terms,
            "intent_source": getattr(intent, "intent_source", "raw_prompt"),
            "control_only_intent": bool(getattr(intent, "control_only_intent", False)),
            "unparsed_prompt_terms": list(getattr(intent, "unparsed_prompt_terms", []) or []),
            "plan_grounding": groundings,
            "prompt_plan_alignment_score": round(alignment_score, 3),
            "measure_count": measure_count,
            "resolved_generation_request": resolved,
            "prompt_ui_conflicts": conflicts,
        }


def build_plan_grounding(intent: Any, measures: list[Any] | None = None) -> dict[str, Any]:
    return PlanGroundingService().build(intent, measures)


def _terms_for_field(terms: list[dict[str, Any]], category: str) -> list[str]:
    if category == "style":
        categories = {"style", "mood"}
    elif category == "rhythm":
        categories = {"rhythm"}
    elif category == "texture":
        categories = {"texture", "accompaniment"}
    else:
        categories = {category}
    return [str(term.get("term")) for term in terms if term.get("category") in categories]

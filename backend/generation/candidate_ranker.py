"""Rank V0.96 generated score candidates before final export."""

from __future__ import annotations

from statistics import mean
from typing import Any

from backend.generation.fingerprint_service import novelty_scores, score_document_fingerprint, score_document_fingerprint_parts


DEFAULT_WEIGHTS = {
    "melody_expectation_score": 0.25,
    "harmony_style_score": 0.2,
    "notation_validity_score": 0.2,
    "melodic_grammar_score": 0.15,
    "style_match_score": 0.1,
    "novelty_score": 0.05,
    "role_coverage_score": 0.05,
    "phrase_contour_score": 0.07,
    "motif_development_score": 0.06,
    "tension_release_score": 0.05,
    "target_tone_hit_score": 0.05,
    "cadence_preparation_score": 0.04,
    "accompaniment_interaction_score": 0.03,
    "mechanical_template_penalty": -0.08,
}


class CandidateRanker:
    """Deterministically score candidates under a fixed candidate set."""

    def rank(self, candidates: list[dict[str, Any]], weights: dict[str, float] | None = None) -> dict[str, Any]:
        weights = {**DEFAULT_WEIGHTS, **(weights or {})}
        fingerprints = [score_document_fingerprint(candidate.get("generated").score_document if candidate.get("generated") else {}) for candidate in candidates]
        part_fingerprints = [score_document_fingerprint_parts(candidate.get("generated").score_document if candidate.get("generated") else {}) for candidate in candidates]
        novelty = novelty_scores(fingerprints)
        scored = []
        for index, candidate in enumerate(candidates):
            metrics = self._candidate_metrics(candidate)
            metrics["novelty_score"] = novelty[index]
            score = sum(float(metrics.get(key, 0.0)) * weight for key, weight in weights.items())
            if float(metrics.get("notation_validity_score", 0.0)) < 1.0:
                score *= 0.35
            report = {
                "candidate_index": int(candidate.get("candidate_index", index)),
                "candidate_seed": int(candidate.get("candidate_seed", 0) or 0),
                "score": round(score, 4),
                "metrics": {key: round(float(value), 4) for key, value in metrics.items()},
                "rejection_reasons": self._rejection_reasons(metrics, candidate),
                "fingerprint": fingerprints[index],
                "fingerprints": part_fingerprints[index],
            }
            scored.append({**candidate, "rank_report": report})
        if not scored:
            raise ValueError("candidate ranking requires at least one candidate")
        selected = max(scored, key=lambda item: (item["rank_report"]["score"], -int(item.get("candidate_index", 0))))
        rejected = [item["rank_report"] for item in scored if item is not selected]
        selected_report = selected["rank_report"]
        diversity = _actual_diversity(part_fingerprints)
        return {
            "selected": selected,
            "candidate_reports": [item["rank_report"] for item in scored],
            "candidate_generation": {
                "run_seed": int(selected.get("parent_run_seed", 0) or 0),
                "candidate_count": len(scored),
                "selected_candidate_index": int(selected.get("candidate_index", 0)),
                "selected_candidate_seed": int(selected.get("candidate_seed", 0) or 0),
                "selected_candidate_score": selected_report["score"],
                "selected_candidate_metrics": selected_report["metrics"],
                "rejected_candidates": rejected,
                "ranking_weights": weights,
                "candidate_actual_diversity": diversity,
            },
        }

    @staticmethod
    def _candidate_metrics(candidate: dict[str, Any]) -> dict[str, float]:
        generated = candidate.get("generated")
        metadata = dict(getattr(generated, "metadata", {}) or {})
        validation = candidate.get("validation")
        expectation = dict(metadata.get("melody_expectation_report") or {})
        grammar = dict(metadata.get("cross_measure_melodic_grammar_report") or metadata.get("melodic_grammar_report") or {})
        musicality = dict(metadata.get("musicality_validation_report") or {})
        role_coverage = dict(metadata.get("role_coverage_report") or {})
        voice_leading = dict(metadata.get("voice_leading_report") or {})
        actual_harmony = dict(metadata.get("actual_harmony_style_report") or {})
        phrase_scores = dict((metadata.get("phrase_melody") or {}).get("phrase_level_scores") or {})
        interaction = dict(metadata.get("accompaniment_interaction_report") or {})
        notation = 1.0 if getattr(validation, "valid", False) else 0.0
        melodic_grammar = 1.0 if grammar.get("valid", True) else 0.55
        if grammar.get("unresolved_tritone_count"):
            melodic_grammar -= 0.25
        roles = [bool(role_coverage.get(key)) for key in ("lead_melody", "harmony", "bass")]
        role_score = sum(1 for item in roles if item) / max(1, len(roles))
        accompaniment = float(musicality.get("left_hand_activity", 0.0) or 0.0)
        harmony_style = float(
            metadata.get(
                "harmony_style_score",
                min(
                    float(voice_leading.get("style_harmony_match_score", 0.75) or 0.75),
                    float(actual_harmony.get("style_harmony_match_score", 0.75) or 0.75),
                ),
            )
            or 0.0
        )
        if actual_harmony.get("plain_triad_only") and str(actual_harmony.get("style")) == "jazz":
            harmony_style = min(harmony_style, 0.35)
        return {
            "melody_expectation_score": float(expectation.get("melody_expectation_score", 0.75) or 0.0),
            "melodic_grammar_score": max(0.0, min(1.0, melodic_grammar)),
            "harmony_style_score": harmony_style,
            "notation_validity_score": notation,
            "style_match_score": float(metadata.get("prompt_plan_alignment_score", 0.8) or 0.8),
            "novelty_score": 0.0,
            "accompaniment_score": max(0.0, min(1.0, accompaniment)),
            "role_coverage_score": max(0.0, min(1.0, mean([role_score, accompaniment]))),
            "phrase_contour_score": float(phrase_scores.get("phrase_contour_score", 0.0) or 0.0),
            "motif_development_score": float(phrase_scores.get("motif_development_score", 0.0) or 0.0),
            "tension_release_score": float(phrase_scores.get("tension_release_score", 0.0) or 0.0),
            "target_tone_hit_score": float(phrase_scores.get("target_tone_hit_score", 0.0) or 0.0),
            "cadence_preparation_score": float(phrase_scores.get("cadence_preparation_score", 0.0) or 0.0),
            "accompaniment_interaction_score": float(
                phrase_scores.get(
                    "accompaniment_interaction_score",
                    0.75 if interaction.get("melody_supported") and interaction.get("cadence_supported") else 0.0,
                )
                or 0.0
            ),
            "mechanical_template_penalty": float(phrase_scores.get("mechanical_template_penalty", 0.0) or 0.0),
        }

    @staticmethod
    def _rejection_reasons(metrics: dict[str, float], candidate: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        if metrics.get("notation_validity_score", 0.0) < 1.0:
            reasons.append("invalid notation")
        if metrics.get("melody_expectation_score", 1.0) < 0.65:
            reasons.append("low melody expectation score")
        if metrics.get("harmony_style_score", 1.0) < 0.65:
            reasons.append("style-inappropriate harmony")
        if metrics.get("melodic_grammar_score", 1.0) < 0.75:
            reasons.append("weak melodic grammar or closure")
        if metrics.get("novelty_score", 1.0) < 0.5:
            reasons.append("near-duplicate candidate")
        if metrics.get("mechanical_template_penalty", 0.0) > 0.35:
            reasons.append("mechanical template-like phrase")
        return reasons or ["lower aggregate rank"]


def rank_candidates(candidates: list[dict[str, Any]], weights: dict[str, float] | None = None) -> dict[str, Any]:
    return CandidateRanker().rank(candidates, weights=weights)


def _actual_diversity(part_fingerprints: list[dict[str, str]]) -> dict[str, float]:
    total = max(1, len(part_fingerprints))
    return {
        "melody_distinct_count": len({item.get("melody", "") for item in part_fingerprints if item.get("melody")}),
        "rhythm_distinct_count": len({item.get("rhythm", "") for item in part_fingerprints if item.get("rhythm")}),
        "harmony_distinct_count": len({item.get("harmony", "") for item in part_fingerprints if item.get("harmony")}),
        "melody_diversity_score": round(len({item.get("melody", "") for item in part_fingerprints if item.get("melody")}) / total, 4),
        "rhythm_diversity_score": round(len({item.get("rhythm", "") for item in part_fingerprints if item.get("rhythm")}) / total, 4),
        "harmony_diversity_score": round(len({item.get("harmony", "") for item in part_fingerprints if item.get("harmony")}) / total, 4),
    }

"""Lightweight symbolic music theory validation."""

from __future__ import annotations

from backend.models.schemas import CompositionPlan, ValidationResult


class TheoryValidator:
    """Check high-level plan consistency before or after generation."""

    def validate_plan(self, plan: CompositionPlan) -> ValidationResult:
        """Validate phrase length, cadence placement, and prompt adherence proxies."""

        issues: list[str] = []
        warnings: list[str] = []
        bars = len(plan.measures)
        if bars not in {8, 16, 32}:
            issues.append(f"Plan has {bars} measures; expected 8, 16, or 32")
        if not plan.measures[-1].cadence:
            warnings.append("Final measure has no explicit cadence")
        if not plan.intent.instruments:
            issues.append("No instrument planned")
        if plan.intent.tempo_bpm < 40 or plan.intent.tempo_bpm > 220:
            issues.append("Tempo outside practical range")

        return ValidationResult(
            valid=not issues,
            issues=issues,
            warnings=warnings,
            metrics={
                "structural_consistency": 1.0 if not issues else 0.5,
                "prompt_adherence_proxy": 0.9 if not warnings else 0.75,
                "measure_count": bars,
            },
        )

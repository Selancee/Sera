"""Stable validation issue and report contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One machine-readable validation finding."""

    code: str
    message: str
    stage: str
    repairable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationReport:
    """Unified report emitted by all SeraEdit validation layers."""

    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)
    suggested_repairs: list[dict[str, Any]] = field(default_factory=list)
    unsupported: bool = False

    @property
    def status(self) -> Literal["valid", "warning", "invalid", "unsupported"]:
        if self.unsupported:
            return "unsupported"
        if self.errors:
            return "invalid"
        if self.warnings:
            return "warning"
        return "valid"

    @property
    def repairable(self) -> bool:
        return bool(self.errors) and all(issue.repairable for issue in self.errors)

    def add_error(self, issue: ValidationIssue) -> None:
        self.errors.append(issue)

    def add_warning(self, issue: ValidationIssue) -> None:
        self.warnings.append(issue)

    def merge(self, other: "ValidationReport", *, check_name: str | None = None) -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.suggested_repairs.extend(other.suggested_repairs)
        self.unsupported = self.unsupported or other.unsupported
        if check_name:
            self.checks[check_name] = other.as_dict()
        else:
            self.checks.update(other.checks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
            "checks": self.checks,
            "repairable": self.repairable,
            "suggested_repairs": self.suggested_repairs,
        }

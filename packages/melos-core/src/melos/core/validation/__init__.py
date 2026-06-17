"""Validation helpers for melos core models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from melos.core.project.model import Project


class ValidationSeverity(StrEnum):
    """Severity level for a validation issue."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(slots=True, kw_only=True)
class ValidationIssue:
    """Single validation issue emitted by a validation pass."""

    code: str
    message: str
    location: str
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass(slots=True, kw_only=True)
class ValidationReport:
    """Aggregate report produced by one or more validation passes."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Return ``True`` if the report contains any errors."""

        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    def extend(self, issues: list[ValidationIssue]) -> None:
        """Append a list of issues to the report."""

        self.issues.extend(issues)

    def add(
        self,
        *,
        code: str,
        message: str,
        location: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> None:
        """Convenience helper to append a single issue."""

        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                location=location,
                severity=severity,
            )
        )


from .references import validate_references
from .topology import validate_topology
from .transforms import validate_transforms


def validate_project(project: Project) -> ValidationReport:
    """Run the standard validation passes for a project."""

    report = ValidationReport()
    report.extend(validate_references(project))
    report.extend(validate_topology(project))
    report.extend(validate_transforms(project))
    return report


__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "validate_project",
    "validate_references",
    "validate_topology",
    "validate_transforms",
]

"""Validation helpers for melos core models."""

from __future__ import annotations

from melos.core.project.model import Project

from .model import ValidationIssue, ValidationReport, ValidationSeverity
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

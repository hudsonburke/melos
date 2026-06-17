"""Validation helpers for Blender-facing feedback."""

from __future__ import annotations

from melos.core.validation import ValidationReport


def format_validation_report(report: ValidationReport) -> list[str]:
    """Format validation issues into concise user-facing strings."""

    if not report.issues:
        return ["No validation issues found."]

    return [
        f"{issue.severity.value.upper()}: {issue.location}: {issue.message}"
        for issue in report.issues
    ]

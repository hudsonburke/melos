"""Import result models for ``melos.sim.mujoco.importers``."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, kw_only=True)
class ImportWarning:
    """Single non-fatal warning emitted during MJCF import."""

    code: str
    message: str
    location: str


@dataclass(slots=True, kw_only=True)
class ImportReport:
    """Aggregate report for an MJCF import pass."""

    warnings: list[ImportWarning] = field(default_factory=list)

    def add_warning(self, *, code: str, message: str, location: str) -> None:
        """Append a warning to the report."""
        self.warnings.append(
            ImportWarning(code=code, message=message, location=location)
        )


@dataclass(slots=True, kw_only=True)
class ImportResult:
    """Primary output of the MJCF importer."""

    project: object
    report: ImportReport = field(default_factory=ImportReport)

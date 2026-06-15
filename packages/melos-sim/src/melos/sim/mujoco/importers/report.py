"""Import and compile report models for ``melos.sim.mujoco``.

Both import and编译 passes emit ``(code, message, location)`` warnings.
Rather than maintain two identical dataclass hierarchies, we keep one pair
(``CompileWarning`` / ``CompileReport``) in ``reports.py`` and expose aliases
here so that ``ImportReport`` / ``ImportWarning`` remain importable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.sim.mujoco.reports import CompileReport, CompileWarning

ImportWarning = CompileWarning
ImportReport = CompileReport


@dataclass(slots=True, kw_only=True)
class ImportResult:
    """Primary output of the MJCF importer."""

    project: object
    report: ImportReport = field(default_factory=ImportReport)
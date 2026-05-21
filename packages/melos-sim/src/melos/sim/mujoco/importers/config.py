"""MJCF SimulationConfig mapper for ``melos.sim.mujoco.importers``."""

from __future__ import annotations

from typing import Any

from melos.core.simulation.enums import IntegratorType, SolverType
from melos.core.simulation.model import SimulationConfig

from .xml_parser import CompilerDirectives
from .report import ImportReport


def map_simulation_config(
    root: Any,
    directives: CompilerDirectives,
    report: ImportReport,
) -> SimulationConfig:
    """Map MJCF ``<option>`` to ``SimulationConfig``."""
    _ = directives
    option = getattr(root, "option", None)
    if option is None:
        return SimulationConfig()

    time_step = _coerce_float(getattr(option, "timestep", None), default=0.001, report=report, code="CONFIG_TIMESTEP_INVALID", field="timestep")

    gravity_value = getattr(option, "gravity", None)
    gravity: tuple[float, float, float] = (0.0, 0.0, -9.81)
    if gravity_value is not None:
        try:
            gravity = tuple(float(v) for v in gravity_value)  # type: ignore[assignment]
            if len(gravity) != 3:
                raise ValueError("expected 3 components")
        except (ValueError, TypeError):
            report.add_warning(
                code="CONFIG_GRAVITY_INVALID",
                message=f"Invalid gravity value: {gravity_value}",
                location="<option>",
            )
            gravity = (0.0, 0.0, -9.81)

    integrator = _enum_value(
        IntegratorType,
        getattr(option, "integrator", None),
        default=IntegratorType.IMPLICITFAST,
        report=report,
        code="CONFIG_INTEGRATOR_INVALID",
        field="integrator",
    )
    solver_type = _enum_value(
        SolverType,
        getattr(option, "solver", None),
        default=SolverType.NEWTON,
        report=report,
        code="CONFIG_SOLVER_INVALID",
        field="solver",
    )
    solver_iterations = _coerce_int(getattr(option, "iterations", None), default=100, report=report, code="CONFIG_ITERATIONS_INVALID", field="iterations")
    solver_tolerance = _coerce_float(getattr(option, "tolerance", None), default=1e-8, report=report, code="CONFIG_TOLERANCE_INVALID", field="tolerance")
    noslip_iterations = _coerce_int(getattr(option, "noslip_iterations", None), default=0, report=report, code="CONFIG_NOSLIP_ITERATIONS_INVALID", field="noslip_iterations")

    return SimulationConfig(
        time_step=time_step,
        gravity=gravity,
        integrator=integrator,
        solver_type=solver_type,
        solver_iterations=solver_iterations,
        solver_tolerance=solver_tolerance,
        noslip_iterations=noslip_iterations,
    )


def _coerce_float(
    value: object,
    *,
    default: float,
    report: ImportReport,
    code: str,
    field: str,
) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        report.add_warning(code=code, message=f"Invalid {field} value: {value}", location="<option>")
        return default


def _coerce_int(
    value: object,
    *,
    default: int,
    report: ImportReport,
    code: str,
    field: str,
) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        report.add_warning(code=code, message=f"Invalid {field} value: {value}", location="<option>")
        return default


def _enum_value(enum_type: type, value: object, *, default: Any, report: ImportReport, code: str, field: str) -> Any:
    if value is None:
        return default
    try:
        return enum_type(str(value).lower())
    except ValueError:
        report.add_warning(code=code, message=f"Unknown {field}: {value} (using default)", location="<option>")
        return default

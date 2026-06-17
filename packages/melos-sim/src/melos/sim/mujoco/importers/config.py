"""ElementTree MJCF SimulationConfig mapper fallback."""

from __future__ import annotations

from xml.etree.ElementTree import Element

from melos.core.simulation.model import IntegratorType, SolverType
from melos.core.simulation.model import SimulationConfig

from .xml_parser import CompilerDirectives
from .report import ImportReport


def map_simulation_config(
    root: Element,
    directives: CompilerDirectives,
    report: ImportReport,
) -> SimulationConfig:
    _ = directives
    option = root.find("option")
    if option is None:
        return SimulationConfig()

    time_step = 0.001
    timestep_str = option.get("timestep")
    if timestep_str is not None:
        try:
            time_step = float(timestep_str)
        except (ValueError, TypeError):
            report.add_warning(
                code="CONFIG_TIMESTEP_INVALID",
                message=f"Invalid timestep value: {timestep_str}",
                location="<option>",
            )

    gravity: tuple[float, float, float] = (0.0, 0.0, -9.81)
    gravity_str = option.get("gravity")
    if gravity_str is not None:
        try:
            gravity_parts = gravity_str.split()
            if len(gravity_parts) == 3:
                gravity = (float(gravity_parts[0]), float(gravity_parts[1]), float(gravity_parts[2]))
            else:
                report.add_warning(
                    code="CONFIG_GRAVITY_INVALID",
                    message=f"Invalid gravity value: {gravity_str} (expected 3 components)",
                    location="<option>",
                )
        except (ValueError, TypeError):
            report.add_warning(
                code="CONFIG_GRAVITY_INVALID",
                message=f"Invalid gravity value: {gravity_str}",
                location="<option>",
            )

    integrator = IntegratorType.IMPLICITFAST
    integrator_str = option.get("integrator")
    if integrator_str is not None:
        try:
            integrator = IntegratorType(integrator_str.lower())
        except ValueError:
            report.add_warning(
                code="CONFIG_INTEGRATOR_INVALID",
                message=f"Unknown integrator: {integrator_str} (using default)",
                location="<option>",
            )
            integrator = IntegratorType.IMPLICITFAST

    solver_type = SolverType.NEWTON
    solver_str = option.get("solver")
    if solver_str is not None:
        _solver_by_lower = {s.value.lower(): s for s in SolverType}
        parsed = _solver_by_lower.get(solver_str.strip().lower())
        if parsed is not None:
            solver_type = parsed
        else:
            report.add_warning(
                code="CONFIG_SOLVER_INVALID",
                message=f"Unknown solver: {solver_str} (using default)",
                location="<option>",
            )

    solver_iterations = 100
    iterations_str = option.get("iterations")
    if iterations_str is not None:
        try:
            solver_iterations = int(iterations_str)
        except (ValueError, TypeError):
            report.add_warning(
                code="CONFIG_ITERATIONS_INVALID",
                message=f"Invalid iterations value: {iterations_str}",
                location="<option>",
            )

    solver_tolerance = 1e-8
    tolerance_str = option.get("tolerance")
    if tolerance_str is not None:
        try:
            solver_tolerance = float(tolerance_str)
        except (ValueError, TypeError):
            report.add_warning(
                code="CONFIG_TOLERANCE_INVALID",
                message=f"Invalid tolerance value: {tolerance_str}",
                location="<option>",
            )

    noslip_iterations = 0
    noslip_iterations_str = option.get("noslip_iterations")
    if noslip_iterations_str is not None:
        try:
            noslip_iterations = int(noslip_iterations_str)
        except (ValueError, TypeError):
            report.add_warning(
                code="CONFIG_NOSLIP_ITERATIONS_INVALID",
                message=f"Invalid noslip_iterations value: {noslip_iterations_str}",
                location="<option>",
            )

    return SimulationConfig(
        time_step=time_step,
        gravity=gravity,
        integrator=integrator,
        solver_type=solver_type,
        solver_iterations=solver_iterations,
        solver_tolerance=solver_tolerance,
        noslip_iterations=noslip_iterations,
    )

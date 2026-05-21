"""Transform-specific and numeric validation for the shared system architecture."""

from __future__ import annotations

from math import isfinite

from melos.core.common.ids import is_valid_identifier
from melos.core.common.transforms import is_finite_transform, is_finite_vec3, quaternion_norm
from melos.core.project.model import Project

from .model import ValidationIssue, ValidationSeverity


def validate_transforms(project: Project) -> list[ValidationIssue]:
    """Validate transforms, numeric values, and identifier form."""

    issues: list[ValidationIssue] = []

    def error(code: str, message: str, location: str) -> None:
        issues.append(ValidationIssue(code=code, message=message, location=location))

    def warning(code: str, message: str, location: str) -> None:
        issues.append(
            ValidationIssue(
                code=code,
                message=message,
                location=location,
                severity=ValidationSeverity.WARNING,
            )
        )

    def require_identifier(value: str, *, location: str, label: str) -> None:
        if not is_valid_identifier(value):
            error("id.invalid", f"{label} {value!r} is not a valid identifier.", location)

    def require_transform(transform, *, location: str, label: str) -> None:
        if not is_finite_transform(transform):
            error("transform.nonfinite", f"{label} has non-finite values.", location)
            return
        norm = quaternion_norm(transform.rotation)
        if norm == 0.0:
            error("transform.zero_quaternion", f"{label} has a zero quaternion.", location)
        elif abs(norm - 1.0) > 1e-6:
            warning(
                "transform.unnormalized_quaternion",
                f"{label} quaternion is not normalized.",
                location,
            )

    def require_nonnegative(value: float | None, *, location: str, label: str) -> None:
        if value is None:
            return
        if not isfinite(value):
            error("value.nonfinite", f"{label} must be finite.", location)
        elif value < 0.0:
            error("value.negative", f"{label} must be non-negative.", location)

    def require_finite_vec3(value, *, location: str, label: str) -> None:
        if value is None:
            return
        if not is_finite_vec3(value):
            error("value.nonfinite", f"{label} must contain only finite values.", location)

    def validate_inertial_properties(inertial, *, location_prefix: str, label_prefix: str) -> None:
        present_fields = [
            inertial.mass is not None,
            inertial.center_of_mass is not None,
            inertial.inertia_about_com is not None,
        ]
        if any(present_fields) and not all(present_fields):
            error(
                "inertial.incomplete",
                f"{label_prefix} inertial properties must define mass, center_of_mass, and inertia_about_com together.",
                location_prefix,
            )
        require_nonnegative(inertial.mass, location=f"{location_prefix}.mass", label=f"{label_prefix} mass")
        require_finite_vec3(
            inertial.center_of_mass,
            location=f"{location_prefix}.center_of_mass",
            label=f"{label_prefix} center_of_mass",
        )
        if inertial.inertia_about_com is not None:
            for index, value in enumerate(inertial.inertia_about_com):
                if not isfinite(value):
                    error(
                        "value.nonfinite",
                        f"{label_prefix} inertia_about_com must contain only finite values.",
                        f"{location_prefix}.inertia_about_com[{index}]",
                    )

    require_identifier(project.meta.id, location="meta.id", label="Project ID")
    require_nonnegative(project.simulation.time_step, location="simulation.time_step", label="Simulation time_step")
    if project.simulation.time_step == 0.0:
        error("value.zero", "Simulation time_step must be greater than zero.", "simulation.time_step")
    require_nonnegative(project.simulation.duration, location="simulation.duration", label="Simulation duration")
    require_finite_vec3(project.simulation.gravity, location="simulation.gravity", label="Simulation gravity")

    for coordinate_id, value in project.simulation.initial_coordinate_values.items():
        require_identifier(
            coordinate_id,
            location=f"simulation.initial_coordinate_values[{coordinate_id}]",
            label="Coordinate ID",
        )
        if not isfinite(value):
            error(
                "value.nonfinite",
                "Initial coordinate value must be finite.",
                f"simulation.initial_coordinate_values[{coordinate_id}]",
            )

    sim = project.simulation
    if sim.solver_iterations < 1:
        error("value.nonpositive", "Solver iterations must be at least 1.", "simulation.solver_iterations")
    if not isfinite(sim.solver_tolerance) or sim.solver_tolerance <= 0.0:
        error(
            "value.nonpositive",
            "Solver tolerance must be a positive finite number.",
            "simulation.solver_tolerance",
        )
    if sim.noslip_iterations < 0:
        error("value.negative", "Noslip iterations must be non-negative.", "simulation.noslip_iterations")
    if sim.record_interval < 1:
        error("value.nonpositive", "Record interval must be at least 1.", "simulation.record_interval")

    for name, values in sim.keyframes.items():
        require_identifier(name, location=f"simulation.keyframes[{name}]", label="Keyframe name")
        for coord_id, value in values.items():
            require_identifier(
                coord_id,
                location=f"simulation.keyframes[{name}][{coord_id}]",
                label="Keyframe coordinate ID",
            )
            if not isfinite(value):
                error(
                    "value.nonfinite",
                    "Keyframe coordinate value must be finite.",
                    f"simulation.keyframes[{name}][{coord_id}]",
                )

    if sim.initial_state_name is not None:
        require_identifier(sim.initial_state_name, location="simulation.initial_state_name", label="Initial state name")
        if sim.initial_state_name not in sim.keyframes:
            warning(
                "simulation.initial_state_name.dangling",
                f"initial_state_name {sim.initial_state_name!r} does not match any keyframe.",
                "simulation.initial_state_name",
            )

    for system in project.systems:
        prefix = f"systems[{system.id}]"
        require_identifier(system.id, location=f"{prefix}.id", label="System ID")

        for link in system.links:
            require_identifier(link.id, location=f"{prefix}.links[{link.id}].id", label="Link ID")
            require_transform(link.transform, location=f"{prefix}.links[{link.id}].transform", label="Link transform")
            if link.inertial is not None:
                validate_inertial_properties(
                    link.inertial,
                    location_prefix=f"{prefix}.links[{link.id}].inertial",
                    label_prefix="Link",
                )

        for site in system.sites:
            require_identifier(site.id, location=f"{prefix}.sites[{site.id}].id", label="Site ID")
            require_transform(site.transform, location=f"{prefix}.sites[{site.id}].transform", label="Site transform")

        for joint in system.joints:
            require_identifier(joint.id, location=f"{prefix}.joints[{joint.id}].id", label="Joint ID")
            for coordinate in joint.coordinates:
                require_identifier(
                    coordinate.id,
                    location=f"{prefix}.joints[{joint.id}].coordinates[{coordinate.id}].id",
                    label="Coordinate ID",
                )
                require_finite_vec3(
                    coordinate.axis,
                    location=f"{prefix}.joints[{joint.id}].coordinates[{coordinate.id}].axis",
                    label="Coordinate axis",
                )
                if coordinate.limits is not None:
                    lower = coordinate.limits.lower
                    upper = coordinate.limits.upper
                    if lower is not None and not isfinite(lower):
                        error(
                            "value.nonfinite",
                            "Coordinate lower bound must be finite.",
                            f"{prefix}.joints[{joint.id}].coordinates[{coordinate.id}].limits.lower",
                        )
                    if upper is not None and not isfinite(upper):
                        error(
                            "value.nonfinite",
                            "Coordinate upper bound must be finite.",
                            f"{prefix}.joints[{joint.id}].coordinates[{coordinate.id}].limits.upper",
                        )
                    if lower is not None and upper is not None and lower > upper:
                        error(
                            "bounds.invalid",
                            "Coordinate lower bound must be less than or equal to upper bound.",
                            f"{prefix}.joints[{joint.id}].coordinates[{coordinate.id}].limits",
                        )

        for geometry in system.geometries:
            require_identifier(
                geometry.id,
                location=f"{prefix}.geometries[{geometry.id}].id",
                label="Geometry ID",
            )
            require_transform(
                geometry.transform,
                location=f"{prefix}.geometries[{geometry.id}].transform",
                label="Geometry transform",
            )

        for actuator in system.actuators:
            require_identifier(
                actuator.id,
                location=f"{prefix}.actuators[{actuator.id}].id",
                label="Actuator ID",
            )
            for label, bounds in (("command_limits", actuator.command_limits), ("output_limits", actuator.output_limits)):
                if bounds is None:
                    continue
                if bounds.lower is not None and not isfinite(bounds.lower):
                    error(
                        "value.nonfinite",
                        f"{label} lower bound must be finite.",
                        f"{prefix}.actuators[{actuator.id}].{label}.lower",
                    )
                if bounds.upper is not None and not isfinite(bounds.upper):
                    error(
                        "value.nonfinite",
                        f"{label} upper bound must be finite.",
                        f"{prefix}.actuators[{actuator.id}].{label}.upper",
                    )
                if bounds.lower is not None and bounds.upper is not None and bounds.lower > bounds.upper:
                    error(
                        "bounds.invalid",
                        f"{label} lower bound must be less than or equal to upper bound.",
                        f"{prefix}.actuators[{actuator.id}].{label}",
                    )

        for sensor in system.sensors:
            require_identifier(
                sensor.id,
                location=f"{prefix}.sensors[{sensor.id}].id",
                label="Sensor ID",
            )


    for assembly in project.assemblies:
        prefix = f"assemblies[{assembly.id}]"
        require_identifier(assembly.id, location=f"{prefix}.id", label="Assembly ID")
        for connection in assembly.connections:
            require_identifier(
                connection.id,
                location=f"{prefix}.connections[{connection.id}].id",
                label="Connection ID",
            )
            require_transform(
                connection.relative_transform,
                location=f"{prefix}.connections[{connection.id}].relative_transform",
                label="Connection relative_transform",
            )
        for coupling in assembly.couplings:
            require_identifier(
                coupling.id,
                location=f"{prefix}.couplings[{coupling.id}].id",
                label="Coupling ID",
            )
            if not isfinite(coupling.scale):
                error(
                    "value.nonfinite",
                    "Coupling scale must be finite.",
                    f"{prefix}.couplings[{coupling.id}].scale",
                )
            if not isfinite(coupling.offset):
                error(
                    "value.nonfinite",
                    "Coupling offset must be finite.",
                    f"{prefix}.couplings[{coupling.id}].offset",
                )

    for observation in project.control.observations:
        require_identifier(
            observation.id,
            location=f"control.observations[{observation.id}].id",
            label="Observation channel ID",
        )

    for command in project.control.commands:
        require_identifier(
            command.id,
            location=f"control.commands[{command.id}].id",
            label="Command channel ID",
        )

    return issues

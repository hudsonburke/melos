"""Topology and structural validation for the shared system architecture."""

from __future__ import annotations

from collections import Counter

from melos.core.project.model import Project
from melos.core.system.enums import ActuatorKind

from . import ValidationIssue, ValidationSeverity


def validate_topology(project: Project) -> list[ValidationIssue]:
    """Validate duplicate IDs and basic structural invariants."""

    issues: list[ValidationIssue] = []

    def add_duplicate_issues(values: list[str], *, location: str, label: str) -> None:
        counts = Counter(values)
        for value, count in sorted(counts.items()):
            if count > 1:
                issues.append(
                    ValidationIssue(
                        code="topology.duplicate_id",
                        message=f"{label} {value!r} appears {count} times.",
                        location=location,
                    )
                )

    add_duplicate_issues([system.id for system in project.systems], location="systems", label="System ID")
    add_duplicate_issues([assembly.id for assembly in project.assemblies], location="assemblies", label="Assembly ID")

    for system in project.systems:
        prefix = f"systems[{system.id}]"
        add_duplicate_issues([link.id for link in system.links], location=f"{prefix}.links", label="Link ID")
        add_duplicate_issues([site.id for site in system.sites], location=f"{prefix}.sites", label="Site ID")
        add_duplicate_issues([joint.id for joint in system.joints], location=f"{prefix}.joints", label="Joint ID")
        add_duplicate_issues(
            [geometry.id for geometry in system.geometries],
            location=f"{prefix}.geometries",
            label="Geometry ID",
        )
        add_duplicate_issues(
            [actuator.id for actuator in system.actuators],
            location=f"{prefix}.actuators",
            label="Actuator ID",
        )
        add_duplicate_issues(
            [sensor.id for sensor in system.sensors],
            location=f"{prefix}.sensors",
            label="Sensor ID",
        )

        child_link_ids = [joint.child_link_id for joint in system.joints]
        add_duplicate_issues(
            child_link_ids,
            location=f"{prefix}.joints.child_link_id",
            label="Joint child link reference",
        )

        for joint in system.joints:
            if joint.parent_link_id is not None and joint.parent_link_id == joint.child_link_id:
                issues.append(
                    ValidationIssue(
                        code="topology.self_parent",
                        message="Joint parent_link_id must differ from child_link_id.",
                        location=f"{prefix}.joints[{joint.id}]",
                    )
                )

        for actuator in system.actuators:
            if actuator.kind != ActuatorKind.CABLE:
                continue
            waypoint_count = len(actuator.route) if actuator.route else len(actuator.site_ids)
            if waypoint_count < 2:
                issues.append(
                    ValidationIssue(
                        code="topology.cable_route_too_short",
                        message=(
                            f"Cable actuator {actuator.id!r} needs at least two routing "
                            f"waypoints; found {waypoint_count}."
                        ),
                        location=f"{prefix}.actuators[{actuator.id}].route",
                        severity=ValidationSeverity.WARNING,
                    )
                )


    for assembly in project.assemblies:
        prefix = f"assemblies[{assembly.id}]"
        add_duplicate_issues(
            [connection.id for connection in assembly.connections],
            location=f"{prefix}.connections",
            label="Connection ID",
        )
        add_duplicate_issues(
            [coupling.id for coupling in assembly.couplings],
            location=f"{prefix}.couplings",
            label="Coupling ID",
        )

        endpoint_attachment_keys = Counter(
            (
                connection.endpoint_a.system_id,
                connection.endpoint_a.anchor_link_id,
                tuple(sorted(connection.endpoint_a.reference_link_ids)),
                tuple(sorted(connection.endpoint_a.reference_site_ids)),
                tuple(sorted(connection.endpoint_a.reference_geometry_ids)),
            )
            for connection in assembly.connections
        )
        for (system_id, anchor_link_id, _link_ids, _site_ids, _geometry_ids), count in sorted(endpoint_attachment_keys.items()):
            if count > 1:
                issues.append(
                    ValidationIssue(
                        code="assembly.endpoint.multiple_connections",
                        message=(
                            f"Assembly endpoint on system {system_id!r} with anchor {anchor_link_id!r} participates in "
                            f"{count} assembly connections."
                        ),
                        location=f"{prefix}.connections",
                        severity=ValidationSeverity.WARNING,
                    )
                )

    add_duplicate_issues(
        [attachment.id for attachment in project.skin_attachments],
        location="skin_attachments",
        label="Skin attachment ID",
    )
    add_duplicate_issues(
        [observation.id for observation in project.control.observations],
        location="control.observations",
        label="Observation channel ID",
    )
    add_duplicate_issues(
        [command.id for command in project.control.commands],
        location="control.commands",
        label="Command channel ID",
    )

    return issues

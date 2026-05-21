"""Assembly and transform helpers for MuJoCo compilation."""

from __future__ import annotations

from dataclasses import dataclass

from melos.core.common.transforms import compose_transforms, rotate_vector
from melos.core.common.types import Transform
from melos.core.project.model import Project
from melos.core.system.model import AssemblyConnection, AssemblyEndpoint, SystemModel

from ..reports import CompileReport


@dataclass(slots=True, kw_only=True)
class AttachmentPlacement:
    """Resolved placement for a system root inferred from an assembly connection."""

    connection_id: str
    transform: Transform


def resolve_system_root_placement(
    project: Project,
    system: SystemModel,
    report: CompileReport,
) -> AttachmentPlacement | None:
    """Resolve the first assembly-backed placement for ``system`` if one exists."""

    for assembly in project.assemblies:
        for connection in assembly.connections:
            placement = _resolve_connection_placement(project, system, connection, report)
            if placement is not None:
                return placement
    return None


def _resolve_connection_placement(
    project: Project,
    system: SystemModel,
    connection: AssemblyConnection,
    report: CompileReport,
) -> AttachmentPlacement | None:
    if connection.endpoint_a.system_id == system.id:
        other_endpoint = connection.endpoint_b
    elif connection.endpoint_b is not None and connection.endpoint_b.system_id == system.id:
        other_endpoint = connection.endpoint_a
    else:
        return None

    if other_endpoint is None:
        return AttachmentPlacement(connection_id=connection.id, transform=connection.relative_transform)

    other_system = project.get_system(other_endpoint.system_id)
    if other_system is None:
        report.add_warning(
            code="assembly.counterpart_system_missing",
            message=(
                f"Assembly connection {connection.id!r} references missing system "
                f"{other_endpoint.system_id!r}; using relative transform only."
            ),
            location=f"assemblies[{connection.id}]",
        )
        return AttachmentPlacement(connection_id=connection.id, transform=connection.relative_transform)

    other_transform = _endpoint_local_transform(other_system, other_endpoint)
    return AttachmentPlacement(
        connection_id=connection.id,
        transform=compose_transforms(other_transform, connection.relative_transform),
    )


def _endpoint_local_transform(system: SystemModel, endpoint: AssemblyEndpoint) -> Transform:
    if endpoint.reference_site_ids:
        site = next(
            (candidate for candidate in system.sites if candidate.id == endpoint.reference_site_ids[0]),
            None,
        )
        if site is not None:
            return site.transform
    if endpoint.anchor_link_id is not None:
        link = next((candidate for candidate in system.links if candidate.id == endpoint.anchor_link_id), None)
        if link is not None:
            return link.transform
    if endpoint.reference_link_ids:
        link = next(
            (candidate for candidate in system.links if candidate.id == endpoint.reference_link_ids[0]),
            None,
        )
        if link is not None:
            return link.transform
    return Transform.identity()


__all__ = ["AttachmentPlacement", "compose_transforms", "resolve_system_root_placement", "rotate_vector"]

"""Adapters that log ``melos.core`` domain models to Rerun.

These functions traverse a melos ``Project``, ``SystemModel``, or plain dict
and log the relevant entities (transforms, meshes, joints, links, sensors,
actuators) using Rerun's built-in archetypes plus the custom components
from ``melos.rerun``.

Entity path convention (shared with MoveDB)::

    {prefix}/skeleton/links/{link_name}       — rr.Transform3D + LinkDefinition
    {prefix}/skeleton/joints/{joint_name}      — melos.rerun.Joint
    {prefix}/skeleton/meshes/{link_name}       — rr.Mesh3D (with transforms)
    {prefix}/simulation/timeline               — Scalars (time-series)
    {prefix}/simulation/sensor/{sensor_name}   — Scalars
"""

from __future__ import annotations

from typing import Any, NamedTuple

import rerun as rr

from .archetypes import Joint, Skeleton


class LogPaths(NamedTuple):
    """Precomputed entity paths for a model entity root."""

    root: str
    skeleton_root: str

    @classmethod
    def from_root(cls, root: str) -> LogPaths:
        base = root.rstrip("/")
        return cls(
            root=base,
            skeleton_root=f"{base}/skeleton",
        )

    def link_path(self, name: str) -> str:
        return f"{self.skeleton_root}/links/{name}"

    def joint_path(self, name: str) -> str:
        return f"{self.skeleton_root}/joints/{name}"

    def mesh_path(self, link_name: str, mesh_name: str = "mesh") -> str:
        return f"{self.skeleton_root}/meshes/{link_name}/{mesh_name}"


# ---------------------------------------------------------------------------
# Low-level log helpers
# ---------------------------------------------------------------------------


def log_joint(
    paths: LogPaths,
    joint_name: str,
    joint_type: str,
    axis: list[float],
    parent_link: str,
    child_link: str,
    limits: dict[str, float] | None = None,
    default_qpos: float = 0.0,
    recording: rr.RecordingStream | None = None,
) -> None:
    """Log a single joint definition at ``paths.joint_path(joint_name)``."""
    rr.log(
        paths.joint_path(joint_name),
        Joint(
            joint_type=joint_type,
            axis=axis,
            parent_link=parent_link,
            child_link=child_link,
            limits=limits,
            default_qpos=default_qpos,
        ),
        recording=recording,
    )


def log_link(
    paths: LogPaths,
    link_name: str,
    parent_link_name: str | None,
    translation: tuple[float, float, float],
    rotation: tuple[float, float, float, float] | None = None,
    mass: float | None = None,
    com: tuple[float, float, float] | None = None,
    recording: rr.RecordingStream | None = None,
) -> None:
    """Log a link as a ``Transform3D`` with optional inertial metadata.

    The ``parent_link_name`` establishes the kinematic hierarchy.  ``None``
    means a root link (parented to the skeleton root).
    """
    path = paths.link_path(link_name)

    # Spatial transform from parent frame
    rr.log(
        path,
        rr.Transform3D(
            translation=translation,
            rotation=rotation,
            # Use implicit frame (tf#) to avoid named-frame conflicts
            # when multiple models are loaded in the same viewer.
            from_parent=True,
        ),
        recording=recording,
    )


def log_mesh(
    paths: LogPaths,
    link_name: str,
    vertex_positions: list[list[float]],
    triangle_indices: list[list[int]] | None = None,
    vertex_colors: list[list[float]] | None = None,
    albedo_factor: list[float] | None = None,
    recording: rr.RecordingStream | None = None,
) -> None:
    """Log a mesh at ``paths.mesh_path(link_name)``, inheriting the link transform."""
    rr.log(
        paths.mesh_path(link_name),
        rr.Mesh3D(
            vertex_positions=vertex_positions,
            triangle_indices=triangle_indices,
            vertex_colors=vertex_colors,
            albedo_factor=albedo_factor,
        ),
        recording=recording,
    )


# ---------------------------------------------------------------------------
# Higher-level helpers that accept melos-core domain objects
# ---------------------------------------------------------------------------


def log_project(
    project: Any,
    *,
    entity_path_prefix: str = "",
    recording: rr.RecordingStream | None = None,
) -> None:
    """Log an entire melos ``Project`` to Rerun.

    This walks ``project.systems`` and logs each as a separate set of entities
    under ``{prefix}/systems/{system_id}``.
    """
    paths = LogPaths.from_root(entity_path_prefix or "/")

    # Project-level metadata as static text
    rr.log(
        paths.root,
        rr.TextDocument(
            f"# {project.meta.name}\n\n{project.meta.description}",
            media_type=rr.MediaType.MARKDOWN,
        ),
        recording=recording,
    )

    # Log each system
    for system in project.systems:
        log_system(
            system,
            entity_path_prefix=f"{paths.root}/systems/{system.id}",
            recording=recording,
        )


def log_system(
    system: Any,
    *,
    entity_path_prefix: str = "",
    recording: rr.RecordingStream | None = None,
) -> None:
    """Log a single melos ``SystemModel`` (anatomical, device, or auxiliary).

    Maps the system's links → ``Transform3D`` and joints → ``melos.rerun.Joint``.
    """
    paths = LogPaths.from_root(entity_path_prefix or "/")

    # Skeleton-level metadata (joints + links as semantic definitions)
    skeleton_joints: list[dict[str, Any]] = []
    for joint in getattr(system, "joints", []) or []:
        skeleton_joints.append({
            "joint_type": joint.kind.value if hasattr(joint.kind, "value") else str(joint.kind),
            "axis": list(joint.axis) if hasattr(joint, "axis") else [0.0, 0.0, 1.0],
            "limits": {
                "lower": joint.limits.lower if hasattr(joint, "limits") and joint.limits else float("-inf"),
                "upper": joint.limits.upper if hasattr(joint, "limits") and joint.limits else float("inf"),
            },
            "parent_link": _link_name(system, joint.parent_link_id) if hasattr(joint, "parent_link_id") else "",
            "child_link": _link_name(system, joint.child_link_id) if hasattr(joint, "child_link_id") else "",
            "default_qpos": getattr(joint, "default_qpos", 0.0) or 0.0,
        })

    skeleton_links: list[dict[str, Any]] = []
    for link in getattr(system, "links", []) or []:
        inertial = getattr(link, "inertial", None) or {}
        skeleton_links.append({
            "name": _safe_name(link),
            "mass": getattr(inertial, "mass", 0.0) or 0.0,
            "com": list(getattr(inertial, "center_of_mass", [0, 0, 0]) or [0, 0, 0]),
        })

    # Log the skeleton archetype for queryability
    rr.log(
        paths.skeleton_root,
        Skeleton(joints=skeleton_joints, links=skeleton_links),
        recording=recording,
    )

    # Log spatial hierarchy via Transform3D
    link_map: dict[str, Any] = {}
    for link in getattr(system, "links", []) or []:
        link_map[_safe_name(link)] = link

    for link in getattr(system, "links", []) or []:
        name = _safe_name(link)
        xform = getattr(link, "transform", None) or {}
        parent_link = _find_parent(system, link)

        log_link(
            paths,
            link_name=name,
            parent_link_name=_safe_name(parent_link) if parent_link else None,
            translation=tuple(getattr(xform, "translation", [0, 0, 0]) or [0, 0, 0]),
            rotation=None,  # will be computed from joint values on update
            mass=getattr(getattr(link, "inertial", None) or {}, "mass", None),
            recording=recording,
        )

    # Log joints individually for selectability
    for joint in getattr(system, "joints", []) or []:
        joint_name = _safe_name(joint)
        log_joint(
            paths,
            joint_name=joint_name,
            joint_type=joint.kind.value if hasattr(joint.kind, "value") else str(joint.kind),
            axis=list(getattr(joint, "axis", [0, 0, 1])),
            parent_link=_link_name(system, joint.parent_link_id) if hasattr(joint, "parent_link_id") else "",
            child_link=_link_name(system, joint.child_link_id) if hasattr(joint, "child_link_id") else "",
            limits={
                "lower": joint.limits.lower if hasattr(joint, "limits") and joint.limits else float("-inf"),
                "upper": joint.limits.upper if hasattr(joint, "limits") and joint.limits else float("inf"),
            } if hasattr(joint, "limits") else None,
            recording=recording,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_name(obj: Any) -> str:
    """Get ``id`` then ``name`` then ``str`` for any object."""
    if hasattr(obj, "id") and obj.id:
        return str(obj.id)
    if hasattr(obj, "name") and obj.name:
        return str(obj.name)
    return str(obj)


def _link_name(system: Any, link_id: Any) -> str:
    """Resolve a link ID reference to a display name."""
    if link_id is None:
        return ""
    link_id_str = str(link_id)
    for link in getattr(system, "links", []) or []:
        if str(link.id) == link_id_str:
            return _safe_name(link)
    return link_id_str


def _find_parent(system: Any, child_link: Any) -> Any | None:
    """Find the parent link of ``child_link`` by scanning joints."""
    child_id = child_link.id if hasattr(child_link, "id") else None
    if child_id is None:
        return None
    child_str = str(child_id)
    joint_parent_map: dict[str, str] = {}
    for joint in getattr(system, "joints", []) or []:
        parent = str(joint.parent_link_id) if hasattr(joint, "parent_link_id") and joint.parent_link_id else ""
        child = str(joint.child_link_id) if hasattr(joint, "child_link_id") and joint.child_link_id else ""
        if child:
            joint_parent_map[child] = parent

    parent_id = joint_parent_map.get(child_str)
    if parent_id:
        for link in getattr(system, "links", []) or []:
            if str(link.id) == parent_id:
                return link
    return None

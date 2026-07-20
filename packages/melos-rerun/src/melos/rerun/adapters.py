"""Adapters that log biomechanical domain models to Rerun.

These functions bridge existing Python data structures (parsed from .osim, .c3d,
or from the Melos editor) to Rerun's entity log, using the canonical component
types from ``melos.rerun``.
"""

from __future__ import annotations

from typing import Any

import rerun as rr

from .archetypes import Joint, Link, Subject


class LogPaths:
    """Precomputed entity paths for a single model root.

    Convention is shared with MoveDB importers so both log to compatible paths.
    """

    def __init__(self, root: str = "") -> None:
        base = root.rstrip("/") if root else ""
        self.root = base
        self.skeleton_root = f"{base}/skeleton"
        self.subject_root = f"{base}/subject"

    def link_path(self, name: str) -> str:
        return f"{self.skeleton_root}/links/{name}"

    def joint_path(self, name: str) -> str:
        return f"{self.skeleton_root}/joints/{name}"

    def mesh_path(self, link_name: str, mesh_name: str = "mesh") -> str:
        return f"{self.skeleton_root}/meshes/{link_name}/{mesh_name}"

    def muscle_path(self, name: str) -> str:
        return f"{self.root}/muscles/{name}"

    def actuator_path(self, name: str) -> str:
        return f"{self.root}/actuators/{name}"


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
    """Log a single joint definition."""
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
    translation: tuple[float, float, float],
    rotation: tuple[float, float, float, float] | None = None,
    mass: float = 0.0,
    parent_from_child: bool = True,
    recording: rr.RecordingStream | None = None,
) -> None:
    """Log a link as ``Transform3D`` + ``LinkDefinition``.

    The transform is the pose of this link relative to its parent frame.
    Pass ``parent_from_child=True`` (default) for the standard kinematic
    hierarchy where the child's transform is expressed in the parent frame.
    """
    path = paths.link_path(link_name)

    rr.log(
        path,
        rr.Transform3D(
            translation=translation,
            rotation=rotation,
            from_parent=parent_from_child,
        ),
        recording=recording,
    )

    rr.log(
        path,
        Link(
            name=link_name,
            mass=mass,
        ),
        recording=recording,
    )


def log_mesh(
    paths: LogPaths,
    link_name: str,
    vertex_positions: list[list[float]],
    triangle_indices: list[list[int]] | None = None,
    vertex_normals: list[list[float]] | None = None,
    recording: rr.RecordingStream | None = None,
) -> None:
    """Log a mesh attached to a link."""
    rr.log(
        paths.mesh_path(link_name),
        rr.Mesh3D(
            vertex_positions=vertex_positions,
            triangle_indices=triangle_indices,
            vertex_normals=vertex_normals,
        ),
        recording=recording,
    )


def log_body_measurements(
    paths: LogPaths,
    measurements: list[dict[str, Any]],
    recording: rr.RecordingStream | None = None,
) -> None:
    """Log subject body measurements (from C3D PROCESSING/SUBJECTS)."""
    rr.log(
        paths.subject_root,
        Subject(measurements=measurements),
        recording=recording,
    )


def log_model_info(
    paths: LogPaths,
    name: str,
    n_bodies: int = 0,
    n_joints: int = 0,
    recording: rr.RecordingStream | None = None,
) -> None:
    """Log a model info text document at the skeleton root."""
    rr.log(
        paths.skeleton_root,
        rr.TextDocument(
            f"# {name}\n\n**Bodies**: {n_bodies}  **Joints**: {n_joints}",
            media_type=rr.MediaType.MARKDOWN,
        ),
        recording=recording,
    )

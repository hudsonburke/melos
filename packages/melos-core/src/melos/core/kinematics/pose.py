"""Pure-Python articulated-system pose evaluation.

Computes link world transforms from a :class:`SystemModel` and optional
coordinate values. Supported joint kinds: FIXED, REVOLUTE, PRISMATIC.
Unsupported kinds raise :class:`NotImplementedError`.
No numpy, no bpy, no MuJoCo imports.
"""

from __future__ import annotations

from math import cos, sin
from typing import TYPE_CHECKING

from melos.core.common.transforms import compose_transforms
from melos.core.common.types import Quat, Transform, Vec3
from melos.core.kinematics.enums import CoordinateKind, JointKind

if TYPE_CHECKING:
    from melos.core.kinematics.model import CoordinateDefinition
    from melos.core.system.model import SystemModel


def evaluate_system_world_transforms(
    system: "SystemModel",
    coordinate_values: dict[str, float] | None = None,
) -> dict[str, Transform]:
    """Return world transforms keyed by link.id for every link in *system*."""

    if coordinate_values is None:
        coordinate_values = {}

    link_map = {link.id: link for link in system.links}

    child_to_joint = {
        joint.child_link_id: joint
        for joint in system.joints
        if joint.child_link_id is not None
    }

    parent_map: dict[str, str | None] = {
        joint.child_link_id: joint.parent_link_id
        for joint in system.joints
        if joint.child_link_id and joint.parent_link_id
    }

    for link_id, link in link_map.items():
        if link_id in parent_map:
            continue
        parent_link = link.annotations.get("mjcf_parent_link") or link.annotations.get("mjcf_parent_body")
        if parent_link is not None and parent_link in link_map:
            parent_map[link_id] = parent_link

    cache: dict[str, Transform] = {}

    def _resolve(link_id: str) -> Transform:
        if link_id in cache:
            return cache[link_id]

        link = link_map[link_id]
        parent_id = parent_map.get(link_id)

        if parent_id is None or parent_id not in link_map:
            world = link.transform
        else:
            rest_world = compose_transforms(_resolve(parent_id), link.transform)
            joint = child_to_joint.get(link_id)
            if joint is not None and joint.coordinates:
                delta = _joint_delta(joint.kind, joint.coordinates, coordinate_values)
                world = compose_transforms(rest_world, delta)
            else:
                world = rest_world

        cache[link_id] = world
        return world

    for link in system.links:
        _resolve(link.id)

    return cache


def _joint_delta(
    kind: JointKind,
    coordinates: "list[CoordinateDefinition]",
    coordinate_values: dict[str, float],
) -> Transform:
    if kind == JointKind.FIXED:
        return Transform.identity()

    if kind == JointKind.REVOLUTE:
        total_rotation: Quat = (1.0, 0.0, 0.0, 0.0)
        for coord in coordinates:
            if coord.kind != CoordinateKind.ROTATION:
                continue
            value = coordinate_values.get(coord.id, coord.default_value)
            total_rotation = _quat_multiply(total_rotation, _axis_angle_to_quat(coord.axis, value))
        return Transform(translation=(0.0, 0.0, 0.0), rotation=total_rotation)

    if kind == JointKind.PRISMATIC:
        tx, ty, tz = 0.0, 0.0, 0.0
        for coord in coordinates:
            if coord.kind != CoordinateKind.TRANSLATION:
                continue
            value = coordinate_values.get(coord.id, coord.default_value)
            ax, ay, az = coord.axis
            norm = (ax * ax + ay * ay + az * az) ** 0.5
            if norm > 0.0:
                ax, ay, az = ax / norm, ay / norm, az / norm
            tx += ax * value
            ty += ay * value
            tz += az * value
        return Transform(translation=(tx, ty, tz), rotation=(1.0, 0.0, 0.0, 0.0))

    raise NotImplementedError(
        f"evaluate_system_world_transforms: joint kind '{kind}' is not supported in v1. "
        "Only FIXED, REVOLUTE, and PRISMATIC joints are handled."
    )


def _axis_angle_to_quat(axis: Vec3, angle: float) -> Quat:
    """Convert an axis + angle (radians) to a ``(w, x, y, z)`` quaternion."""
    ax, ay, az = axis
    norm = (ax * ax + ay * ay + az * az) ** 0.5
    if norm == 0.0:
        return (1.0, 0.0, 0.0, 0.0)
    ax, ay, az = ax / norm, ay / norm, az / norm
    half = angle * 0.5
    s = sin(half)
    return (cos(half), ax * s, ay * s, az * s)


def _quat_multiply(lhs: Quat, rhs: Quat) -> Quat:
    """Hamilton product of two ``(w, x, y, z)`` quaternions."""
    lw, lx, ly, lz = lhs
    rw, rx, ry, rz = rhs
    return (
        lw * rw - lx * rx - ly * ry - lz * rz,
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
    )

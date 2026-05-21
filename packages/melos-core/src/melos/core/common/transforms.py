"""Transform conventions and helper utilities."""

from __future__ import annotations

from math import isfinite, sqrt

from .types import Quat, Transform, Vec3


def is_finite_vec3(vector: Vec3) -> bool:
    """Return ``True`` when all vector components are finite."""

    return all(isfinite(component) for component in vector)


def is_finite_quaternion(quaternion: Quat) -> bool:
    """Return ``True`` when all quaternion components are finite."""

    return all(isfinite(component) for component in quaternion)


def quaternion_norm(quaternion: Quat) -> float:
    """Return the Euclidean norm of a quaternion."""

    return sqrt(sum(component * component for component in quaternion))


def normalize_quaternion(quaternion: Quat) -> Quat:
    """Return a normalized quaternion.

    The melos core model uses quaternions in ``(w, x, y, z)`` order.
    """

    norm = quaternion_norm(quaternion)
    if norm == 0.0:
        raise ValueError("Cannot normalize a zero quaternion.")

    return tuple(component / norm for component in quaternion)  # type: ignore[return-value]


def normalize_quaternion_or_identity(quaternion: Quat) -> Quat:
    norm = quaternion_norm(quaternion)
    if norm == 0.0:
        return (1.0, 0.0, 0.0, 0.0)

    return tuple(component / norm for component in quaternion)  # type: ignore[return-value]


def is_finite_transform(transform: Transform) -> bool:
    """Return ``True`` when both translation and rotation are finite."""

    return is_finite_vec3(transform.translation) and is_finite_quaternion(
        transform.rotation
    )


def compose_transforms(parent: Transform, child: Transform) -> Transform:
    """Compose two transforms using melos's ``(w, x, y, z)`` quaternions."""

    rotated_translation = rotate_vector(parent.rotation, child.translation)
    translation: Vec3 = (
        parent.translation[0] + rotated_translation[0],
        parent.translation[1] + rotated_translation[1],
        parent.translation[2] + rotated_translation[2],
    )
    return Transform(
        translation=translation,
        rotation=normalize_quaternion_or_identity(
            multiply_quaternions(parent.rotation, child.rotation)
        ),
    )


def rotate_vector(rotation: Quat, vector: Vec3) -> Vec3:
    """Rotate a vector by a quaternion."""

    vector_quaternion = (0.0, vector[0], vector[1], vector[2])
    rotated = multiply_quaternions(
        multiply_quaternions(rotation, vector_quaternion),
        quaternion_conjugate(rotation),
    )
    return (rotated[1], rotated[2], rotated[3])


def multiply_quaternions(lhs: Quat, rhs: Quat) -> Quat:
    """Multiply two ``(w, x, y, z)`` quaternions."""

    lw, lx, ly, lz = lhs
    rw, rx, ry, rz = rhs
    return (
        lw * rw - lx * rx - ly * ry - lz * rz,
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
    )

def quaternion_conjugate(quaternion: Quat) -> Quat:
    """Return the conjugate of a quaternion."""

    w, x, y, z = quaternion
    return (w, -x, -y, -z)

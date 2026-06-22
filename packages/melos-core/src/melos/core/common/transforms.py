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


# ---------------------------------------------------------------------------
# Vec3 helpers
# ---------------------------------------------------------------------------

def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    """Element-wise addition of two 3-vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    """Element-wise subtraction of two 3-vectors."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec3_scale(v: Vec3, scalar: float) -> Vec3:
    """Scale a 3-vector by a scalar."""
    return (v[0] * scalar, v[1] * scalar, v[2] * scalar)


def vec3_dot(a: Vec3, b: Vec3) -> float:
    """Dot product of two 3-vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vec3_cross(a: Vec3, b: Vec3) -> Vec3:
    """Cross product of two 3-vectors."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vec3_length(v: Vec3) -> float:
    """Euclidean length of a 3-vector."""
    from math import sqrt
    return sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def vec3_normalize(v: Vec3) -> Vec3:
    """Return a unit-length copy of *v*. Returns zero vector if *v* is near-zero."""
    magnitude = vec3_length(v)
    if magnitude < 1e-8:
        return (0.0, 0.0, 0.0)
    return (v[0] / magnitude, v[1] / magnitude, v[2] / magnitude)


def vec3_centroid(points: list[Vec3]) -> Vec3:
    """Arithmetic mean of a list of 3-vectors."""
    n = len(points)
    return (
        sum(p[0] for p in points) / n,
        sum(p[1] for p in points) / n,
        sum(p[2] for p in points) / n,
    )


def axis_angle_to_quat(axis: Vec3, angle: float) -> Quat:
    """Convert an axis + angle (radians) to a ``(w, x, y, z)`` quaternion.

    Returns the identity quaternion if *axis* is zero-length.
    """
    norm = vec3_length(axis)
    if norm < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    ax, ay, az = axis[0] / norm, axis[1] / norm, axis[2] / norm
    from math import cos, sin
    half = angle * 0.5
    s = sin(half)
    return (cos(half), ax * s, ay * s, az * s)

"""Shared MJCF quaternion conversion utilities.

Both the ``dm_control`` and ElementTree importers need the same set of
rotation-format conversions. Consolidated here to eliminate duplication.
"""

from __future__ import annotations

import math


_MERGEABLE_SECTION_TAGS = {
    "asset",
    "actuator",
    "contact",
    "default",
    "equality",
    "sensor",
    "tendon",
    "worldbody",
}


def euler_to_quat(euler_str: str) -> tuple[float, float, float, float]:
    """Convert an MJCF ``euler`` attribute string (XYZ radians) to ``(w, x, y, z)``."""
    ex, ey, ez = [float(x) for x in euler_str.split()]
    cx, sx = math.cos(ex / 2), math.sin(ex / 2)
    cy, sy = math.cos(ey / 2), math.sin(ey / 2)
    cz, sz = math.cos(ez / 2), math.sin(ez / 2)
    w = cx * cy * cz + sx * sy * sz
    x = sx * cy * cz - cx * sy * sz
    y = cx * sy * cz + sx * cy * sz
    z = cx * cy * sz - sx * sy * cz
    return (w, x, y, z)


def axisangle_to_quat(ax: float, ay: float, az: float, angle: float) -> tuple[float, float, float, float]:
    """Convert an axis + angle (radians) to ``(w, x, y, z)``."""
    from melos.core.common.transforms import axis_angle_to_quat
    return axis_angle_to_quat((ax, ay, az), angle)


def xyaxes_to_quat(xx: float, xy: float, xz: float, yx: float, yy: float, yz: float) -> tuple[float, float, float, float]:
    """Convert an MJCF ``xyaxes`` attribute to ``(w, x, y, z)``."""
    zx = xy * yz - xz * yy
    zy = xz * yx - xx * yz
    zz = xx * yy - xy * yx
    r00, r01, r02 = xx, yx, zx
    r10, r11, r12 = xy, yy, zy
    r20, r21, r22 = xz, yz, zz
    trace = r00 + r11 + r22
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (r21 - r12) * s
        y = (r02 - r20) * s
        z = (r10 - r01) * s
    elif r00 > r11 and r00 > r22:
        s = 2.0 * math.sqrt(1.0 + r00 - r11 - r22)
        w = (r21 - r12) / s
        x = 0.25 * s
        y = (r01 + r10) / s
        z = (r02 + r20) / s
    elif r11 > r22:
        s = 2.0 * math.sqrt(1.0 + r11 - r00 - r22)
        w = (r02 - r20) / s
        x = (r01 + r10) / s
        y = 0.25 * s
        z = (r12 + r21) / s
    else:
        s = 2.0 * math.sqrt(1.0 + r22 - r00 - r11)
        w = (r10 - r01) / s
        x = (r02 + r20) / s
        y = (r12 + r21) / s
        z = 0.25 * s
    return (w, x, y, z)


def zaxis_to_quat(zx: float, zy: float, zz: float) -> tuple[float, float, float, float]:
    """Convert an MJCF ``zaxis`` attribute to ``(w, x, y, z)``."""
    mag = math.sqrt(zx * zx + zy * zy + zz * zz)
    if mag < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    zx, zy, zz = zx / mag, zy / mag, zz / mag
    ref = (1.0, 0.0, 0.0) if abs(zx) < 0.9 else (0.0, 1.0, 0.0)
    xx = ref[1] * zz - ref[2] * zy
    xy = ref[2] * zx - ref[0] * zz
    xz = ref[0] * zy - ref[1] * zx
    xmag = math.sqrt(xx * xx + xy * xy + xz * xz)
    xx, xy, xz = xx / xmag, xy / xmag, xz / xmag
    yx = zy * xz - zz * xy
    yy = zz * xx - zx * xz
    yz = zx * xy - zy * xx
    return xyaxes_to_quat(xx, xy, xz, yx, yy, yz)


def parse_vec3(s: str) -> tuple[float, float, float]:
    """Parse an MJCF space-separated 3-float string."""
    parts = s.split()
    return (float(parts[0]), float(parts[1]), float(parts[2]))


def parse_quat(s: str) -> tuple[float, float, float, float]:
    """Parse an MJCF space-separated 4-float string as ``(w, x, y, z)``."""
    parts = s.split()
    return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))


def build_quat_annotation_from_attrs(
    quat_str: str | None,
    euler_str: str | None,
    axisangle_str: str | None,
    xyaxes_str: str | None,
    zaxis_str: str | None,
) -> str | None:
    """Derive a ``(w, x, y, z)`` quaternion string from MJCF rotation attributes.

    Returns ``None`` if no rotation attribute is set.
    """
    if quat_str is not None:
        return quat_str

    if euler_str is not None:
        w, x, y, z = euler_to_quat(euler_str)
        return f"{w} {x} {y} {z}"

    if axisangle_str is not None:
        parts = axisangle_str.split()
        w, x, y, z = axisangle_to_quat(float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
        return f"{w} {x} {y} {z}"

    if xyaxes_str is not None:
        parts = xyaxes_str.split()
        w, x, y, z = xyaxes_to_quat(
            float(parts[0]), float(parts[1]), float(parts[2]),
            float(parts[3]), float(parts[4]), float(parts[5]),
        )
        return f"{w} {x} {y} {z}"

    if zaxis_str is not None:
        parts = zaxis_str.split()
        w, x, y, z = zaxis_to_quat(float(parts[0]), float(parts[1]), float(parts[2]))
        return f"{w} {x} {y} {z}"

    return None
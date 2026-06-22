"""Shared MJCF quaternion conversion utilities."""

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
    """Convert an MJCF ``euler`` attribute string (ZYX intrinsic rotation, radians) to ``(w, x, y, z)``.

    MuJoCo's ``euler`` attribute applies rotations as follows:
    first around Z by ez, then around Y' by ey, then around X'' by ex.
    This is intrinsic ZYX (a.k.a. extrinsic XYZ).
    """
    ex, ey, ez = [float(x) for x in euler_str.split()]
    cx, sx = math.cos(ex / 2), math.sin(ex / 2)
    cy, sy = math.cos(ey / 2), math.sin(ey / 2)
    cz, sz = math.cos(ez / 2), math.sin(ez / 2)
    w = cx * cy * cz - sx * sy * sz
    x = sx * cy * cz + cx * sy * sz
    y = cx * sy * cz - sx * cy * sz
    z = cx * cy * sz + sx * sy * cz
    return (w, x, y, z)
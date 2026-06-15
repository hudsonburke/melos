"""ElementTree MJCF body hierarchy and inertial mapper fallback."""

from __future__ import annotations

import math
from dataclasses import dataclass
from xml.etree.ElementTree import Element

from melos.core.common.mechanics import InertialProperties
from melos.core.common.types import Transform
from melos.core.system.model import Link

from .defaults import DefaultClassMap, apply_defaults, get_active_class
from .report import ImportReport


@dataclass(slots=True, kw_only=True)
class BodyInfo:
    name: str
    parent_name: str | None
    element: Element
    child_class: str | None = None


BodyTree = dict[str, BodyInfo]


def euler_to_quat(euler_str: str) -> tuple[float, float, float, float]:
    ex, ey, ez = [float(x) for x in euler_str.split()]
    cx, sx = math.cos(ex / 2), math.sin(ex / 2)
    cy, sy = math.cos(ey / 2), math.sin(ey / 2)
    cz, sz = math.cos(ez / 2), math.sin(ez / 2)
    w = cx * cy * cz + sx * sy * sz
    x = sx * cy * cz - cx * sy * sz
    y = cx * sy * cz + sx * cy * sz
    z = cx * cy * sz - sx * sy * cz
    return (w, x, y, z)


def _parse_inertial(element: Element) -> InertialProperties | None:
    inertial_el = element.find("inertial")
    if inertial_el is None:
        return None

    mass_str = inertial_el.get("mass")
    pos_str = inertial_el.get("pos")
    fullinertia_str = inertial_el.get("fullinertia")

    mass = float(mass_str) if mass_str is not None else None

    com = None
    if pos_str is not None:
        parts = pos_str.split()
        com = (float(parts[0]), float(parts[1]), float(parts[2]))

    inertia = None
    if fullinertia_str is not None:
        parts = fullinertia_str.split()
        inertia = (
            float(parts[0]),
            float(parts[1]),
            float(parts[2]),
            float(parts[3]),
            float(parts[4]),
            float(parts[5]),
        )

    return InertialProperties(mass=mass, center_of_mass=com, inertia_about_com=inertia)


def _collect_mesh_asset_ids(element: Element) -> list[str]:
    ids: list[str] = []
    for child in element:
        if child.tag == "geom":
            mesh_name = child.get("mesh")
            if mesh_name is not None:
                ids.append(mesh_name)
    return ids


def _axisangle_to_quat(ax: float, ay: float, az: float, angle: float) -> tuple[float, float, float, float]:
    mag = math.sqrt(ax * ax + ay * ay + az * az)
    if mag < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    ax, ay, az = ax / mag, ay / mag, az / mag
    half = angle / 2.0
    s = math.sin(half)
    return (math.cos(half), ax * s, ay * s, az * s)


def _xyaxes_to_quat(xx: float, xy: float, xz: float, yx: float, yy: float, yz: float) -> tuple[float, float, float, float]:
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


def _zaxis_to_quat(zx: float, zy: float, zz: float) -> tuple[float, float, float, float]:
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
    return _xyaxes_to_quat(xx, xy, xz, yx, yy, yz)


def _build_quat_annotation(element: Element) -> str | None:
    quat_str = element.get("quat")
    if quat_str is not None:
        return quat_str

    euler_str = element.get("euler")
    if euler_str is not None:
        w, x, y, z = euler_to_quat(euler_str)
        return f"{w} {x} {y} {z}"

    axisangle_str = element.get("axisangle")
    if axisangle_str is not None:
        parts = axisangle_str.split()
        w, x, y, z = _axisangle_to_quat(float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
        return f"{w} {x} {y} {z}"

    xyaxes_str = element.get("xyaxes")
    if xyaxes_str is not None:
        parts = xyaxes_str.split()
        w, x, y, z = _xyaxes_to_quat(
            float(parts[0]), float(parts[1]), float(parts[2]),
            float(parts[3]), float(parts[4]), float(parts[5]),
        )
        return f"{w} {x} {y} {z}"

    zaxis_str = element.get("zaxis")
    if zaxis_str is not None:
        parts = zaxis_str.split()
        w, x, y, z = _zaxis_to_quat(float(parts[0]), float(parts[1]), float(parts[2]))
        return f"{w} {x} {y} {z}"

    return None


def _parse_vec3(s: str) -> tuple[float, float, float]:
    parts = s.split()
    return (float(parts[0]), float(parts[1]), float(parts[2]))


def _parse_quat(s: str) -> tuple[float, float, float, float]:
    parts = s.split()
    return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))


def _walk_bodies(
    element: Element,
    parent_name: str | None,
    parent_class: str | None,
    defaults: DefaultClassMap,
    report: ImportReport,
    links_out: list[Link],
    tree_out: BodyTree,
) -> None:
    for child in element:
        if child.tag != "body":
            continue

        name = child.get("name")
        if not name:
            report.add_warning(
                code="MISSING_BODY_NAME",
                message="<body> element has no name attribute",
                location="worldbody",
            )
            continue

        active_class = get_active_class(child, parent_class)
        apply_defaults(child, active_class, defaults)

        inertial = _parse_inertial(child)
        asset_ids = _collect_mesh_asset_ids(child)

        annotations: dict[str, str] = {}
        pos_str = child.get("pos")
        if pos_str is not None:
            annotations["mjcf_pos"] = pos_str
        if parent_name is not None:
            annotations["mjcf_parent_body"] = parent_name

        quat_annotation = _build_quat_annotation(child)
        if quat_annotation is not None:
            annotations["mjcf_quat"] = quat_annotation

        pos_vec = _parse_vec3(pos_str) if pos_str is not None else (0.0, 0.0, 0.0)
        quat_vec = _parse_quat(quat_annotation) if quat_annotation is not None else (1.0, 0.0, 0.0, 0.0)

        link = Link(
            id=name,
            name=name,
            transform=Transform(translation=pos_vec, rotation=quat_vec),
            inertial=inertial,
            asset_ids=asset_ids,
            annotations=annotations,
        )
        links_out.append(link)

        child_class = child.get("childclass", active_class)
        tree_out[name] = BodyInfo(name=name, parent_name=parent_name, element=child, child_class=child_class)
        _walk_bodies(child, name, child_class, defaults, report, links_out, tree_out)


def map_bodies(
    worldbody: Element,
    defaults: DefaultClassMap,
    report: ImportReport,
) -> tuple[list[Link], BodyTree]:
    links: list[Link] = []
    tree: BodyTree = {}
    _walk_bodies(worldbody, None, None, defaults, report, links, tree)
    return links, tree

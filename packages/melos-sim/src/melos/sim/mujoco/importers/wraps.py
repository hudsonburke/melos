"""ElementTree MJCF wrap geometry mapper fallback."""

from __future__ import annotations

from xml.etree.ElementTree import Element

from melos.core.common.types import Transform
from melos.core.common.enums import GeometryRole
from melos.core.system.model import Geometry

from .bodies import BodyTree
from .quat_utils import euler_to_quat
from .defaults import DefaultClassMap
from .report import ImportReport


def map_wrap_geometries(
    worldbody: Element,
    tendon_section: Element | None,
    body_tree: BodyTree,
    defaults: DefaultClassMap,
    report: ImportReport,
) -> tuple[list[Geometry], dict[str, str]]:
    _ = worldbody, defaults, report
    tendon_geom_names: set[str] = set()
    if tendon_section is not None:
        for geom_el in tendon_section.iter("geom"):
            ref = geom_el.get("geom")
            if ref is not None:
                tendon_geom_names.add(ref)

    wraps: list[Geometry] = []

    for body_info in body_tree.values():
        body_el = body_info.element
        for geom_el in body_el:
            if geom_el.tag != "geom":
                continue

            geom_name = geom_el.get("name")
            if not geom_name:
                continue

            geom_type = geom_el.get("type", "sphere")
            if geom_type not in ("sphere", "cylinder"):
                continue

            is_wrap = (
                geom_name in tendon_geom_names
                or geom_el.get("group") == "2"
                or (geom_el.get("contype") == "0" and geom_el.get("conaffinity") == "0")
            )
            if not is_wrap:
                continue

            size_str = geom_el.get("size", "")
            size_parts = [float(s) for s in size_str.split()]
            parameters: dict[str, object]
            if geom_type == "sphere":
                parameters = {"radius": size_parts[0]}
            else:
                parameters = {"radius": size_parts[0], "height": size_parts[1] * 2.0}

            pos_str = geom_el.get("pos")
            quat_str = geom_el.get("quat")
            if quat_str is None and geom_el.get("euler") is not None:
                w, x, y, z = euler_to_quat(geom_el.get("euler", "0 0 0"))
                quat_str = f"{w} {x} {y} {z}"

            translation = (
                tuple(float(v) for v in pos_str.split())
                if pos_str is not None
                else (0.0, 0.0, 0.0)
            )
            rotation = (
                tuple(float(v) for v in quat_str.split())
                if quat_str is not None
                else (1.0, 0.0, 0.0, 0.0)
            )

            wraps.append(
                Geometry(
                    id=geom_name,
                    name=geom_name,
                    kind=geom_type,
                    role=GeometryRole.WRAP,
                    link_id=body_info.name,
                    transform=Transform(translation=translation, rotation=rotation),
                    parameters=parameters,
                )
            )

    geom_name_to_wrap_id: dict[str, str] = {wrap.name: wrap.id for wrap in wraps}
    return wraps, geom_name_to_wrap_id

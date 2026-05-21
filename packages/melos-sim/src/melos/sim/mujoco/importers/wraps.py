"""MJCF wrap geometry mapper for ``melos.sim.mujoco.importers``."""

from __future__ import annotations

from typing import Any

from melos.core.common.types import Transform
from melos.core.system.enums import GeometryRole
from melos.core.system.model import Geometry

from .bodies import BodyTree, _build_quat_annotation, _commit_defaults_if_supported
from .report import ImportReport


def map_wrap_geometries(
    tendon_section: Any | None,
    body_tree: BodyTree,
    report: ImportReport,
) -> tuple[list[Geometry], dict[str, str]]:
    _ = report
    tendon_geom_names: set[str] = set()
    if tendon_section is not None:
        for spatial in getattr(tendon_section, "spatial", []):
            for child in spatial.all_children():
                if child.tag != "geom":
                    continue
                ref = getattr(getattr(child, "geom", None), "name", None)
                if ref is not None:
                    tendon_geom_names.add(str(ref))

    wraps: list[Geometry] = []

    for body_info in body_tree.values():
        for geom_el in getattr(body_info.element, "geom", []):
            _commit_defaults_if_supported(geom_el)

            geom_name = getattr(geom_el, "name", None)
            if not geom_name:
                continue

            geom_type = str(getattr(geom_el, "type", None) or "sphere")
            if geom_type not in ("sphere", "cylinder"):
                continue

            group = getattr(geom_el, "group", None)
            contype = getattr(geom_el, "contype", None)
            conaffinity = getattr(geom_el, "conaffinity", None)
            is_wrap = (
                str(geom_name) in tendon_geom_names
                or str(group) == "2"
                or (str(contype) == "0" and str(conaffinity) == "0")
            )
            if not is_wrap:
                continue

            size_values = getattr(geom_el, "size", None)
            if size_values is None:
                continue
            size_parts = [float(s) for s in size_values]
            parameters: dict[str, object]
            if geom_type == "sphere":
                parameters = {"radius": size_parts[0]}
            else:
                parameters = {"radius": size_parts[0], "height": size_parts[1] * 2.0}

            translation = (
                tuple(float(v) for v in geom_el.pos)
                if getattr(geom_el, "pos", None) is not None
                else (0.0, 0.0, 0.0)
            )
            quat_str = _build_quat_annotation(geom_el)
            rotation = _parse_quat(quat_str) if quat_str is not None else (1.0, 0.0, 0.0, 0.0)

            wraps.append(
                Geometry(
                    id=str(geom_name),
                    name=str(geom_name),
                    kind=geom_type,
                    role=GeometryRole.WRAP,
                    link_id=body_info.name,
                    transform=Transform(translation=translation, rotation=rotation),
                    parameters=parameters,
                )
            )

    geom_name_to_wrap_id: dict[str, str] = {wrap.name: wrap.id for wrap in wraps}
    return wraps, geom_name_to_wrap_id


def _parse_quat(s: str) -> tuple[float, float, float, float]:
    parts = s.split()
    return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))

"""ElementTree MJCF site and muscle mapper fallback."""

from __future__ import annotations

from xml.etree.ElementTree import Element

from melos.core.common.types import Transform
from melos.core.system.enums import ActuatorKind
from melos.core.system.model import Actuator, Site

from .bodies import BodyTree
from .defaults import DefaultClassMap, apply_defaults, get_active_class
from .report import ImportReport


def map_muscle_physiology(
    actuator_section: Element,
    defaults: DefaultClassMap,
    report: ImportReport,
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for el in actuator_section:
        if el.tag != "muscle":
            continue
        name = el.get("name")
        if not name:
            report.add_warning(
                code="muscle.missing_name",
                message="<muscle> element has no name attribute, skipping",
                location="actuator",
            )
            continue
        apply_defaults(el, get_active_class(el, None), defaults)
        result[name] = _extract_physiology(el, name, report)
    return result


def _extract_physiology(
    el: Element,
    name: str,
    report: ImportReport,
) -> dict[str, float]:
    result: dict[str, float] = {}

    force_str = el.get("force")
    if force_str is not None:
        result["max_isometric_force"] = float(force_str)

    range_str = el.get("range")
    lengthrange_str = el.get("lengthrange")

    if lengthrange_str is not None and range_str is not None:
        lr0, lr1 = (float(v) for v in lengthrange_str.split())
        r0, r1 = (float(v) for v in range_str.split())
        range_span = r1 - r0
        if abs(range_span) > 1e-12:
            result["optimal_fiber_length"] = (lr1 - lr0) / range_span
            result["tendon_slack_length"] = lr0 - result["optimal_fiber_length"] * r0
    elif lengthrange_str is None:
        report.add_warning(
            code="muscle.missing_lengthrange",
            message=f"Muscle '{name}' has no lengthrange attribute; ofl and tsl cannot be computed",
            location=f"actuator/muscle[@name='{name}']",
        )

    for key in ("lmin", "lmax", "fpmax"):
        value = el.get(key)
        if value is not None:
            result[key] = float(value)

    return result


def map_sites(
    worldbody: Element,
    report: ImportReport,
) -> list[Site]:
    sites: list[Site] = []

    def _walk(el: Element, parent_body_name: str | None) -> None:
        for child in el:
            if child.tag == "body":
                _walk(child, child.get("name"))
                continue
            if child.tag != "site":
                continue
            name = child.get("name")
            if not name:
                report.add_warning(
                    code="site.missing_name",
                    message="<site> element has no name attribute; skipping",
                    location=f"body:{parent_body_name or 'world'}",
                )
                continue
            pos_str = child.get("pos", "0 0 0")
            quat_str = child.get("quat")
            x, y, z = (float(v) for v in pos_str.split())
            rotation = (
                tuple(float(v) for v in quat_str.split())
                if quat_str is not None
                else (1.0, 0.0, 0.0, 0.0)
            )
            sites.append(
                Site(
                    id=name,
                    name=name,
                    link_id=parent_body_name,
                    transform=Transform(translation=(x, y, z), rotation=rotation),
                    tags=["mjcf_site"],
                )
            )

    _walk(worldbody, None)
    return sites


def map_muscle_paths(
    tendon_section: Element | None,
    worldbody: Element,
    wrap_geom_map: dict[str, str],
    body_tree: BodyTree,
    report: ImportReport,
) -> list[Actuator]:
    _ = worldbody, body_tree, report
    if tendon_section is None:
        return []

    muscles: list[Actuator] = []

    for spatial in tendon_section:
        if spatial.tag != "spatial":
            continue

        name_raw = spatial.get("name") or ""
        muscle_id = name_raw.removesuffix("_tendon") if name_raw.endswith("_tendon") else name_raw

        site_ids: list[str] = []
        wrap_ids: list[str] = []

        for child in spatial:
            if child.tag == "site":
                ref = child.get("site", "")
                if ref:
                    site_ids.append(ref)
            elif child.tag == "geom":
                geom_name = child.get("geom", "")
                if geom_name:
                    wrap_ids.append(wrap_geom_map.get(geom_name, geom_name))

        muscles.append(
            Actuator(
                id=muscle_id,
                name=muscle_id,
                kind=ActuatorKind.MUSCLE,
                site_ids=site_ids,
                parameters={"wrap_geometry_ids": wrap_ids},
            )
        )

    return muscles

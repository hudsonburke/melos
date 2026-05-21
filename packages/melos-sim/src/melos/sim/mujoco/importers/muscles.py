"""MJCF site and muscle mapper for ``melos.sim.mujoco.importers``."""

from __future__ import annotations

from typing import Any

from melos.core.common.types import Transform
from melos.core.system.enums import ActuatorKind
from melos.core.system.model import Actuator, Site

from .bodies import _commit_defaults_if_supported
from .report import ImportReport


def map_muscle_physiology(
    actuator_section: Any,
    report: ImportReport,
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for el in getattr(actuator_section, "muscle", []):
        _commit_defaults_if_supported(el)
        name = getattr(el, "name", None)
        if not name:
            report.add_warning(
                code="muscle.missing_name",
                message="<muscle> element has no name attribute, skipping",
                location="actuator",
            )
            continue
        result[str(name)] = _extract_physiology(el, str(name), report)
    return result


def _extract_physiology(
    el: Any,
    name: str,
    report: ImportReport,
) -> dict[str, float]:
    result: dict[str, float] = {}

    force_value = getattr(el, "force", None)
    if force_value is not None:
        result["max_isometric_force"] = float(force_value)

    range_values = getattr(el, "range", None)
    lengthrange_values = getattr(el, "lengthrange", None)

    if lengthrange_values is not None and range_values is not None:
        lr0, lr1 = (float(v) for v in lengthrange_values)
        r0, r1 = (float(v) for v in range_values)
        range_span = r1 - r0
        if abs(range_span) > 1e-12:
            result["optimal_fiber_length"] = (lr1 - lr0) / range_span
            result["tendon_slack_length"] = lr0 - result["optimal_fiber_length"] * r0
    elif lengthrange_values is None:
        report.add_warning(
            code="muscle.missing_lengthrange",
            message=f"Muscle '{name}' has no lengthrange attribute; ofl and tsl cannot be computed",
            location=f"actuator/muscle[@name='{name}']",
        )

    for key in ("lmin", "lmax", "fpmax"):
        value = getattr(el, key, None)
        if value is not None:
            result[key] = float(value)

    return result


def map_sites(
    worldbody: Any,
    report: ImportReport,
) -> list[Site]:
    """Map MJCF ``<site>`` elements to shared ``Site`` objects."""

    sites: list[Site] = []

    def _walk(body_parent: Any, parent_body_name: str | None) -> None:
        for body in getattr(body_parent, "body", []):
            body_name = getattr(body, "name", None)
            _walk(body, str(body_name) if body_name is not None else None)
        for child in getattr(body_parent, "site", []):
            _commit_defaults_if_supported(child)
            name = getattr(child, "name", None)
            if not name:
                report.add_warning(
                    code="site.missing_name",
                    message="<site> element has no name attribute; skipping",
                    location=f"body:{parent_body_name or 'world'}",
                )
                continue
            translation = (
                tuple(float(v) for v in child.pos)
                if getattr(child, "pos", None) is not None
                else (0.0, 0.0, 0.0)
            )
            rotation = (
                tuple(float(v) for v in child.quat)
                if getattr(child, "quat", None) is not None
                else (1.0, 0.0, 0.0, 0.0)
            )
            sites.append(
                Site(
                    id=str(name),
                    name=str(name),
                    link_id=parent_body_name,
                    transform=Transform(translation=translation, rotation=rotation),
                    tags=["mjcf_site"],
                )
            )

    _walk(worldbody, None)
    return sites


def map_muscle_paths(
    tendon_section: Any | None,
    wrap_geom_map: dict[str, str],
    report: ImportReport,
) -> list[Actuator]:
    """Map MJCF ``<tendon><spatial>`` elements to muscle actuators."""
    _ = report
    if tendon_section is None:
        return []

    muscles: list[Actuator] = []

    for spatial in getattr(tendon_section, "spatial", []):
        name_raw = getattr(spatial, "name", "") or ""
        muscle_id = name_raw.removesuffix("_tendon") if str(name_raw).endswith("_tendon") else str(name_raw)

        site_ids: list[str] = []
        wrap_ids: list[str] = []

        for child in spatial.all_children():
            if child.tag == "site":
                ref = getattr(getattr(child, "site", None), "name", None)
                if ref:
                    site_ids.append(str(ref))
            elif child.tag == "geom":
                geom_name = getattr(getattr(child, "geom", None), "name", None)
                if geom_name:
                    wrap_ids.append(wrap_geom_map.get(str(geom_name), str(geom_name)))

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

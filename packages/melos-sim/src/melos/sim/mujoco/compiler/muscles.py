"""Muscle and wrap helpers for MuJoCo compilation."""

from __future__ import annotations

from melos.core.common.enums import GeometryRole
from melos.core.system.model import Actuator, Geometry

from ..reports import CompileReport


def get_wrap_geom_spec(
    geometry: Geometry,
    report: CompileReport,
) -> tuple[str, str] | None:
    """Return MuJoCo geom type and size string for supported wrap geometries."""

    if geometry.role != GeometryRole.WRAP:
        return None

    parameters = geometry.parameters
    if geometry.kind == "cylinder":
        radius = parameters.get("radius")
        height = parameters.get("height")
        if isinstance(radius, (int, float)) and isinstance(height, (int, float)):
            return ("cylinder", _format_scalars(float(radius), float(height) / 2.0))
    if geometry.kind == "sphere":
        radius = parameters.get("radius")
        if isinstance(radius, (int, float)):
            return ("sphere", _format_scalars(float(radius)))
    if geometry.kind == "ellipsoid":
        rx = parameters.get("radius_x")
        ry = parameters.get("radius_y")
        rz = parameters.get("radius_z")
        if all(isinstance(value, (int, float)) for value in (rx, ry, rz)):
            return ("ellipsoid", _format_scalars(float(rx), float(ry), float(rz)))

    report.add_warning(
        code="wrap.unsupported_kind",
        message=(
            f"Wrap geometry {geometry.id!r} uses kind {geometry.kind!r}, which is not "
            "yet lowered into MJCF."
        ),
        location=f"systems[*].geometries[{geometry.id}]",
    )
    return None


def build_muscle_site_sequence(
    actuator: Actuator,
    site_name_by_site_id: dict[tuple[str, str], str],
    system_id: str,
    report: CompileReport,
) -> list[str]:
    """Return the ordered MuJoCo site names used by a muscle actuator."""

    wrap_ids = actuator.parameters.get("wrap_geometry_ids", [])
    if wrap_ids:
        report.add_warning(
            code="muscle.wrap.approximation",
            message=(
                f"Muscle {actuator.id!r} references wrap geometries, but the initial "
                "MuJoCo compiler emits a site-only tendon path approximation."
            ),
            location=f"systems[{system_id}].actuators[{actuator.id}].parameters.wrap_geometry_ids",
        )

    return [
        site_name_by_site_id[(system_id, site_id)]
        for site_id in actuator.site_ids
        if (system_id, site_id) in site_name_by_site_id
    ]


def _format_scalars(*values: float) -> str:
    return " ".join(f"{value:.6g}" for value in values)

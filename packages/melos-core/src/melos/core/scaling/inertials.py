"""Scaling functions for inertial properties, wrap geometries, and contact geometries."""

from __future__ import annotations

from melos.core.system.model import InertialProperties
from melos.core.common.types import Transform, Vec3
from melos.core.system.contact import ContactGeometry
from melos.core.scaling.factors import ScaleFactorMap
from melos.core.muscles.wraps import (
    CylinderWrapParameters,
    EllipsoidWrapParameters,
    SphereWrapParameters,
    TorusWrapParameters,
    WrapGeometry,
    WrapParameters,
)


def scale_inertial(
    inertial: InertialProperties | None, scale_factor: float
) -> InertialProperties | None:
    """Scale inertial properties by a uniform scale factor.

    - mass scales by scale³
    - center_of_mass scales linearly
    - inertia_about_com scales by scale⁵
    """
    if inertial is None:
        return None

    new_mass = (
        inertial.mass * (scale_factor**3) if inertial.mass is not None else None
    )

    new_com: Vec3 | None = None
    if inertial.center_of_mass is not None:
        cx, cy, cz = inertial.center_of_mass
        new_com = (cx * scale_factor, cy * scale_factor, cz * scale_factor)

    new_inertia: tuple[float, float, float, float, float, float] | None = None
    if inertial.inertia_about_com is not None:
        s5 = scale_factor**5
        ixx, iyy, izz, ixy, ixz, iyz = inertial.inertia_about_com
        new_inertia = (ixx * s5, iyy * s5, izz * s5, ixy * s5, ixz * s5, iyz * s5)

    return InertialProperties(
        mass=new_mass,
        center_of_mass=new_com,
        inertia_about_com=new_inertia,
    )


def _scale_wrap_parameters(params: WrapParameters, sf: float) -> WrapParameters:
    """Return a new scaled copy of wrap parameters."""
    if params is None:
        return None
    if isinstance(params, CylinderWrapParameters):
        return CylinderWrapParameters(radius=params.radius * sf, height=params.height * sf)
    if isinstance(params, SphereWrapParameters):
        return SphereWrapParameters(radius=params.radius * sf)
    if isinstance(params, EllipsoidWrapParameters):
        return EllipsoidWrapParameters(
            radius_x=params.radius_x * sf,
            radius_y=params.radius_y * sf,
            radius_z=params.radius_z * sf,
        )
    if isinstance(params, TorusWrapParameters):
        return TorusWrapParameters(
            minor_radius=params.minor_radius * sf,
            major_radius=params.major_radius * sf,
        )
    # Unknown type — return as-is (no mutation)
    return params


def scale_wrap_geometries(
    wraps: list[WrapGeometry],
    scale_factors: ScaleFactorMap,
    frame_to_body: dict[str, str] | None = None,
) -> list[WrapGeometry]:
    """Return a new list of WrapGeometry objects with scaled transforms and parameters.

    Does NOT mutate input objects.
    """
    result: list[WrapGeometry] = []
    for wrap in wraps:
        link_id = wrap.link_id
        if link_id is None and wrap.site_id is not None and frame_to_body is not None:
            link_id = frame_to_body.get(wrap.site_id)

        sf = scale_factors.get(link_id, 1.0) if link_id is not None else 1.0

        old_t = wrap.transform.translation
        new_translation: Vec3 = (old_t[0] * sf, old_t[1] * sf, old_t[2] * sf)
        new_transform = Transform(translation=new_translation, rotation=wrap.transform.rotation)

        new_params = _scale_wrap_parameters(wrap.parameters, sf)

        result.append(
            WrapGeometry(
                id=wrap.id,
                name=wrap.name,
                kind=wrap.kind,
                link_id=wrap.link_id,
                site_id=wrap.site_id,
                transform=new_transform,
                parameters=new_params,
                asset_id=wrap.asset_id,
                description=wrap.description,
                annotations=wrap.annotations,
            )
        )
    return result


def scale_contact_geometries(
    contacts: list[ContactGeometry],
    scale_factors: ScaleFactorMap,
    frame_to_body: dict[str, str] | None = None,
) -> list[ContactGeometry]:
    """Return a new list of ContactGeometry objects with scaled transforms and sizes.

    Does NOT mutate input objects.
    """
    result: list[ContactGeometry] = []
    for contact in contacts:
        body_id = contact.link_id
        if body_id is None and contact.site_id is not None and frame_to_body is not None:
            body_id = frame_to_body.get(contact.site_id)

        sf = scale_factors.get(body_id, 1.0) if body_id is not None else 1.0

        old_t = contact.transform.translation
        new_translation: Vec3 = (old_t[0] * sf, old_t[1] * sf, old_t[2] * sf)
        new_transform = Transform(translation=new_translation, rotation=contact.transform.rotation)

        old_sz = contact.size
        new_size: Vec3 = (old_sz[0] * sf, old_sz[1] * sf, old_sz[2] * sf)

        result.append(
            ContactGeometry(
                id=contact.id,
                name=contact.name,
                kind=contact.kind,
                link_id=contact.link_id,
                site_id=contact.site_id,
                transform=new_transform,
                size=new_size,
                asset_id=contact.asset_id,
                description=contact.description,
                annotations=contact.annotations,
            )
        )
    return result

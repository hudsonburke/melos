from __future__ import annotations

import pytest

from melos.core.common.types import InertialProperties, Transform
from melos.core.contact.model import ContactGeometryKind
from melos.core.contact.model import ContactGeometry
from melos.core.scaling.inertials import (
    scale_contact_geometries,
    scale_inertial,
    scale_wrap_geometries,
)
from melos.core.actuator.muscles.enums import WrapGeometryKind
from melos.core.actuator.muscles.wraps import (
    CylinderWrapParameters,
    EllipsoidWrapParameters,
    SphereWrapParameters,
    TorusWrapParameters,
    WrapGeometry,
)


def _make_wrap(
    wrap_id: str,
    link_id: str | None = "body1",
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    kind: WrapGeometryKind = WrapGeometryKind.CYLINDER,
    parameters=None,
) -> WrapGeometry:
    return WrapGeometry(
        id=wrap_id,
        name=wrap_id,
        kind=kind,
        link_id=link_id,
        transform=Transform(translation=translation),
        parameters=parameters,
    )


def _make_contact(
    contact_id: str,
    link_id: str | None = "body1",
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    size: tuple[float, float, float] = (0.1, 0.1, 0.1),
) -> ContactGeometry:
    return ContactGeometry(
        id=contact_id,
        name=contact_id,
        kind=ContactGeometryKind.SPHERE,
        link_id=link_id,
        transform=Transform(translation=translation),
        size=size,
    )


def test_inertial_none_returns_none():
    assert scale_inertial(None, 2.0) is None


def test_inertial_mass_scales_by_cube():
    inertial = InertialProperties(mass=100.0)
    result = scale_inertial(inertial, 2.0)
    assert result is not None
    assert result.mass == pytest.approx(800.0)


def test_inertial_com_scales_linearly():
    inertial = InertialProperties(center_of_mass=(0.1, 0.2, 0.3))
    result = scale_inertial(inertial, 3.0)
    assert result is not None
    assert result.center_of_mass == pytest.approx((0.3, 0.6, 0.9))


def test_inertial_inertia_scales_by_fifth_power():
    inertial = InertialProperties(inertia_about_com=(1.0, 1.0, 1.0, 0.0, 0.0, 0.0))
    result = scale_inertial(inertial, 2.0)
    assert result is not None
    assert result.inertia_about_com == pytest.approx((32.0, 32.0, 32.0, 0.0, 0.0, 0.0))


def test_inertial_none_fields_stay_none():
    inertial = InertialProperties()
    result = scale_inertial(inertial, 2.0)
    assert result is not None
    assert result.mass is None
    assert result.center_of_mass is None
    assert result.inertia_about_com is None


def test_cylinder_wrap_scales():
    params = CylinderWrapParameters(radius=0.05, height=0.1)
    wrap = _make_wrap("w1", parameters=params)
    scaled = scale_wrap_geometries([wrap], {"body1": 2.0})
    p = scaled[0].parameters
    assert isinstance(p, CylinderWrapParameters)
    assert p.radius == pytest.approx(0.1)
    assert p.height == pytest.approx(0.2)


def test_sphere_wrap_scales():
    params = SphereWrapParameters(radius=0.03)
    wrap = _make_wrap("w1", kind=WrapGeometryKind.SPHERE, parameters=params)
    scaled = scale_wrap_geometries([wrap], {"body1": 3.0})
    p = scaled[0].parameters
    assert isinstance(p, SphereWrapParameters)
    assert p.radius == pytest.approx(0.09)


def test_ellipsoid_wrap_scales():
    params = EllipsoidWrapParameters(radius_x=0.1, radius_y=0.2, radius_z=0.3)
    wrap = _make_wrap("w1", kind=WrapGeometryKind.ELLIPSOID, parameters=params)
    scaled = scale_wrap_geometries([wrap], {"body1": 2.0})
    p = scaled[0].parameters
    assert isinstance(p, EllipsoidWrapParameters)
    assert p.radius_x == pytest.approx(0.2)
    assert p.radius_y == pytest.approx(0.4)
    assert p.radius_z == pytest.approx(0.6)


def test_torus_wrap_scales():
    params = TorusWrapParameters(minor_radius=0.01, major_radius=0.05)
    wrap = _make_wrap("w1", kind=WrapGeometryKind.TORUS, parameters=params)
    scaled = scale_wrap_geometries([wrap], {"body1": 4.0})
    p = scaled[0].parameters
    assert isinstance(p, TorusWrapParameters)
    assert p.minor_radius == pytest.approx(0.04)
    assert p.major_radius == pytest.approx(0.20)


def test_wrap_none_params_unchanged():
    wrap = _make_wrap("w1", parameters=None)
    scaled = scale_wrap_geometries([wrap], {"body1": 2.0})
    assert scaled[0].parameters is None


def test_wrap_transform_translation_scales():
    wrap = _make_wrap("w1", translation=(0.1, 0.2, 0.3))
    scaled = scale_wrap_geometries([wrap], {"body1": 2.0})
    t = scaled[0].transform.translation
    assert t == pytest.approx((0.2, 0.4, 0.6))
    assert scaled[0].transform.rotation == wrap.transform.rotation


def test_contact_size_scales():
    contact = _make_contact("c1", size=(0.1, 0.2, 0.3))
    scaled = scale_contact_geometries([contact], {"body1": 2.0})
    assert scaled[0].size == pytest.approx((0.2, 0.4, 0.6))


def test_contact_transform_translation_scales():
    contact = _make_contact("c1", translation=(0.05, 0.1, 0.15))
    scaled = scale_contact_geometries([contact], {"body1": 3.0})
    t = scaled[0].transform.translation
    assert t == pytest.approx((0.15, 0.3, 0.45))
    assert scaled[0].transform.rotation == contact.transform.rotation


def test_input_not_mutated():
    params = CylinderWrapParameters(radius=0.05, height=0.1)
    wrap = _make_wrap("w1", translation=(0.1, 0.2, 0.3), parameters=params)
    _ = scale_wrap_geometries([wrap], {"body1": 5.0})
    assert wrap.transform.translation == (0.1, 0.2, 0.3)
    assert isinstance(wrap.parameters, CylinderWrapParameters)
    assert wrap.parameters.radius == pytest.approx(0.05)
    assert wrap.parameters.height == pytest.approx(0.1)

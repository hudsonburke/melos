"""Wrap-geometry definitions for muscle actuators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

from melos.core.common.ids import Identifier
from melos.core.common.metadata import AnnotationMap
from melos.core.common.types import Transform
from melos.core.common.units import LENGTH_UNIT
from .enums import WrapGeometryKind


@dataclass(slots=True, kw_only=True)
class CylinderWrapParameters:
    """Cylinder wrap dimensions."""

    radius: float = field(metadata={"unit": LENGTH_UNIT})
    height: float = field(metadata={"unit": LENGTH_UNIT})


@dataclass(slots=True, kw_only=True)
class SphereWrapParameters:
    """Sphere wrap dimensions."""

    radius: float = field(metadata={"unit": LENGTH_UNIT})


@dataclass(slots=True, kw_only=True)
class EllipsoidWrapParameters:
    """Ellipsoid wrap dimensions."""

    radius_x: float = field(metadata={"unit": LENGTH_UNIT})
    radius_y: float = field(metadata={"unit": LENGTH_UNIT})
    radius_z: float = field(metadata={"unit": LENGTH_UNIT})


@dataclass(slots=True, kw_only=True)
class TorusWrapParameters:
    """Torus wrap dimensions."""

    minor_radius: float = field(metadata={"unit": LENGTH_UNIT})
    major_radius: float = field(metadata={"unit": LENGTH_UNIT})


WrapParameters: TypeAlias = (
    CylinderWrapParameters
    | SphereWrapParameters
    | EllipsoidWrapParameters
    | TorusWrapParameters
    | None
)


@dataclass(slots=True, kw_only=True)
class WrapGeometry:
    """Actuator-associated geometry that influences muscle path evaluation.

    ``parameters`` uses typed dataclasses for common wrap archetypes so the
    schema is easier to validate and compile downstream.
    """

    id: Identifier
    name: str
    kind: WrapGeometryKind
    link_id: Identifier | None = None
    site_id: Identifier | None = None
    transform: Transform = field(default_factory=Transform.identity)
    parameters: WrapParameters = None
    asset_id: Identifier | None = None
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)

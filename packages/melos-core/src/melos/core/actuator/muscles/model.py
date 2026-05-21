"""Canonical muscle-actuator model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.ids import LandmarkId, LinkId, SiteId
from melos.core.common.metadata import AnnotationMap
from melos.core.common.types import Vec3, ZERO_VEC3
from melos.core.common.units import ANGLE_UNIT, FORCE_UNIT, LENGTH_UNIT
from .enums import MusclePathPointKind
from .geometry import MuscleGeometry, MuscleSimulationHints
from .ids import MuscleId, MusclePathPointId, WrapGeometryId


@dataclass(slots=True, kw_only=True)
class MusclePhysiology:
    """Physiological properties associated with a musculotendon unit."""

    max_isometric_force: float | None = field(default=None, metadata={"unit": FORCE_UNIT})
    optimal_fiber_length: float | None = field(default=None, metadata={"unit": LENGTH_UNIT})
    tendon_slack_length: float | None = field(default=None, metadata={"unit": LENGTH_UNIT})
    pennation_angle: float | None = field(default=None, metadata={"unit": ANGLE_UNIT})
    specific_tension: float | None = None
    description: str = ""


@dataclass(slots=True, kw_only=True)
class MusclePathPoint:
    """Ordered point contributing to the canonical muscle path."""

    id: MusclePathPointId
    name: str
    kind: MusclePathPointKind
    link_id: LinkId | None = None
    site_id: SiteId | None = None
    landmark_id: LandmarkId | None = None
    position: Vec3 = field(default=ZERO_VEC3, metadata={"unit": LENGTH_UNIT})
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class MusclePath:
    """Canonical line-of-action definition for a muscle."""

    points: list[MusclePathPoint] = field(default_factory=list)
    wrap_geometry_ids: list[WrapGeometryId] = field(default_factory=list)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class MuscleModel:
    """Top-level muscle actuator model.

    The canonical definition is the physiology plus the ordered path. Optional
    associated geometry can support visualization, fitting, or future
    higher-fidelity volumetric representations without replacing the canonical
    path-based definition.
    """

    id: MuscleId
    name: str
    path: MusclePath = field(default_factory=MusclePath)
    physiology: MusclePhysiology | None = None
    geometry: MuscleGeometry | None = None
    simulation_hints: MuscleSimulationHints | None = None
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)

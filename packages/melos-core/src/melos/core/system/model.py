"""Shared articulated-system model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.ids import (
    ActuatorId,
    AssetId,
    AssemblyId,
    ConnectionId,
    CoordinateId,
    CouplingId,
    GeometryId,
    JointId,
    LinkId,
    SensorId,
    SiteId,
    SystemId,
)
from melos.core.common.metadata import AnnotationMap
from melos.core.common.mechanics import InertialProperties
from melos.core.common.types import Bounds, Transform
from melos.core.kinematics.enums import JointKind
from melos.core.kinematics.model import CoordinateDefinition

from .enums import (
    ActuatorKind,
    ConnectionKind,
    ConstraintPolicy,
    GeometryRole,
    InterfaceKind,
    SensorKind,
    SystemRole,
)


@dataclass(slots=True, kw_only=True)
class Link:
    """Generic rigid link/body shared by subjects and devices."""

    id: LinkId
    name: str
    transform: Transform = field(default_factory=Transform.identity)
    inertial: InertialProperties | None = None
    asset_ids: list[AssetId] = field(default_factory=list)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Site:
    """Named point or frame attached to a link or another site."""

    id: SiteId
    name: str
    link_id: LinkId | None = None
    parent_site_id: SiteId | None = None
    transform: Transform = field(default_factory=Transform.identity)
    tags: list[str] = field(default_factory=list)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Joint:
    """Generic joint connecting two links through optional sites."""

    id: JointId
    name: str
    kind: JointKind
    parent_link_id: LinkId | None = None
    child_link_id: LinkId
    parent_site_id: SiteId | None = None
    child_site_id: SiteId | None = None
    coordinates: list[CoordinateDefinition] = field(default_factory=list)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Geometry:
    """Generic geometry attached to a link or site."""

    id: GeometryId
    name: str
    kind: str
    role: GeometryRole = GeometryRole.CUSTOM
    link_id: LinkId | None = None
    site_id: SiteId | None = None
    transform: Transform = field(default_factory=Transform.identity)
    parameters: dict[str, object] = field(default_factory=dict)
    asset_id: AssetId | None = None
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Actuator:
    """Generic actuator primitive shared across systems."""

    id: ActuatorId
    name: str
    kind: ActuatorKind
    joint_id: JointId | None = None
    coordinate_id: CoordinateId | None = None
    link_ids: list[LinkId] = field(default_factory=list)
    site_ids: list[SiteId] = field(default_factory=list)
    command_limits: Bounds | None = None
    output_limits: Bounds | None = None
    parameters: dict[str, object] = field(default_factory=dict)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Sensor:
    """Generic sensor primitive shared across systems."""

    id: SensorId
    name: str
    kind: SensorKind
    link_id: LinkId | None = None
    site_id: SiteId | None = None
    measurement_unit: str = ""
    parameters: dict[str, object] = field(default_factory=dict)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class AssemblyEndpoint:
    """Contextual attachment endpoint referencing one system's native primitives."""

    system_id: SystemId
    kind: InterfaceKind = InterfaceKind.CUSTOM
    anchor_link_id: LinkId | None = None
    reference_link_ids: list[LinkId] = field(default_factory=list)
    reference_site_ids: list[SiteId] = field(default_factory=list)
    reference_geometry_ids: list[GeometryId] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    fit_metadata: AnnotationMap = field(default_factory=dict)
    compliance_metadata: AnnotationMap = field(default_factory=dict)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class CoordinateCoupling:
    """Generic coupling between two generalized coordinates."""

    id: CouplingId
    name: str
    source_coordinate_id: CoordinateId
    target_coordinate_id: CoordinateId
    scale: float = 1.0
    offset: float = 0.0
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class AssemblyConnection:
    """Connection between one or two contextual assembly endpoints."""

    id: ConnectionId
    name: str
    endpoint_a: AssemblyEndpoint
    endpoint_b: AssemblyEndpoint | None = None
    relative_transform: Transform = field(default_factory=Transform.identity)
    connection_kind: ConnectionKind = ConnectionKind.RIGID
    constraint_policy: ConstraintPolicy | None = None
    fit_state: AnnotationMap = field(default_factory=dict)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class SystemAssembly:
    """Interface-centric assembly connecting one or more systems."""

    id: AssemblyId = "assembly"
    name: str = "assembly"
    connections: list[AssemblyConnection] = field(default_factory=list)
    couplings: list[CoordinateCoupling] = field(default_factory=list)
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class SystemModel:
    """Shared articulated-system container for subjects and devices."""

    id: SystemId
    name: str
    role: SystemRole = SystemRole.CUSTOM
    root_link_id: LinkId | None = None
    description: str = ""
    asset_ids: list[AssetId] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    joints: list[Joint] = field(default_factory=list)
    sites: list[Site] = field(default_factory=list)
    geometries: list[Geometry] = field(default_factory=list)
    actuators: list[Actuator] = field(default_factory=list)
    sensors: list[Sensor] = field(default_factory=list)
    profile: AnnotationMap = field(default_factory=dict)
    annotations: AnnotationMap = field(default_factory=dict)

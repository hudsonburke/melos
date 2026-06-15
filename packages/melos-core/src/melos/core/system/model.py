"""Shared articulated-system model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.ids import Identifier
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
    RouteNodeKind,
    SensorKind,
    SystemRole,
)


@dataclass(slots=True, kw_only=True)
class Link:
    """Generic rigid link/body shared by subjects and devices."""

    id: Identifier
    name: str
    transform: Transform = field(default_factory=Transform.identity)
    inertial: InertialProperties | None = None
    asset_ids: list[Identifier] = field(default_factory=list)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Site:
    """Named point or frame attached to a link or another site."""

    id: Identifier
    name: str
    link_id: Identifier | None = None
    parent_site_id: Identifier | None = None
    transform: Transform = field(default_factory=Transform.identity)
    tags: list[str] = field(default_factory=list)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Joint:
    """Generic joint connecting two links through optional sites."""

    id: Identifier
    name: str
    kind: JointKind
    parent_link_id: Identifier | None = None
    child_link_id: Identifier
    parent_site_id: Identifier | None = None
    child_site_id: Identifier | None = None
    coordinates: list[CoordinateDefinition] = field(default_factory=list)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Geometry:
    """Generic geometry attached to a link or site."""

    id: Identifier
    name: str
    kind: str
    role: GeometryRole = GeometryRole.CUSTOM
    link_id: Identifier | None = None
    site_id: Identifier | None = None
    transform: Transform = field(default_factory=Transform.identity)
    parameters: dict[str, object] = field(default_factory=dict)
    asset_id: Identifier | None = None
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class RouteNode:
    """Ordered waypoint in an actuator routing path."""

    kind: RouteNodeKind = RouteNodeKind.SITE
    site_id: Identifier | None = None
    geometry_id: Identifier | None = None
    side_site_id: Identifier | None = None


@dataclass(slots=True, kw_only=True)
class CableParameters:
    """Typed tendon/cable parameters for routed actuators (SI units)."""

    rest_length: float | None = None
    stiffness: float = 0.0
    damping: float = 0.0
    pre_tension: float = 0.0
    width: float | None = None
    length_range: Bounds | None = None


@dataclass(slots=True, kw_only=True)
class Actuator:
    """Generic actuator primitive shared across systems."""

    id: Identifier
    name: str
    kind: ActuatorKind
    joint_id: Identifier | None = None
    coordinate_id: Identifier | None = None
    link_ids: list[Identifier] = field(default_factory=list)
    site_ids: list[Identifier] = field(default_factory=list)
    route: list[RouteNode] = field(default_factory=list)
    cable: CableParameters | None = None
    command_limits: Bounds | None = None
    output_limits: Bounds | None = None
    parameters: dict[str, object] = field(default_factory=dict)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Sensor:
    """Generic sensor primitive shared across systems."""

    id: Identifier
    name: str
    kind: SensorKind
    link_id: Identifier | None = None
    site_id: Identifier | None = None
    measurement_unit: str = ""
    parameters: dict[str, object] = field(default_factory=dict)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class AssemblyEndpoint:
    """Contextual attachment endpoint referencing one system's native primitives."""

    system_id: Identifier
    kind: InterfaceKind = InterfaceKind.CUSTOM
    anchor_link_id: Identifier | None = None
    reference_link_ids: list[Identifier] = field(default_factory=list)
    reference_site_ids: list[Identifier] = field(default_factory=list)
    reference_geometry_ids: list[Identifier] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class CoordinateCoupling:
    """Generic coupling between two generalized coordinates."""

    id: Identifier
    name: str
    source_coordinate_id: Identifier
    target_coordinate_id: Identifier
    scale: float = 1.0
    offset: float = 0.0
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class AssemblyConnection:
    """Connection between one or two contextual assembly endpoints."""

    id: Identifier
    name: str
    endpoint_a: AssemblyEndpoint
    endpoint_b: AssemblyEndpoint | None = None
    relative_transform: Transform = field(default_factory=Transform.identity)
    connection_kind: ConnectionKind = ConnectionKind.RIGID
    constraint_policy: ConstraintPolicy | None = None
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class SystemAssembly:
    """Interface-centric assembly connecting one or more systems."""

    id: Identifier = "assembly"
    name: str = "assembly"
    connections: list[AssemblyConnection] = field(default_factory=list)
    couplings: list[CoordinateCoupling] = field(default_factory=list)
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class SystemModel:
    """Shared articulated-system container for subjects and devices."""

    id: Identifier
    name: str
    role: SystemRole = SystemRole.CUSTOM
    root_link_id: Identifier | None = None
    description: str = ""
    asset_ids: list[Identifier] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    joints: list[Joint] = field(default_factory=list)
    sites: list[Site] = field(default_factory=list)
    geometries: list[Geometry] = field(default_factory=list)
    actuators: list[Actuator] = field(default_factory=list)
    sensors: list[Sensor] = field(default_factory=list)
    annotations: AnnotationMap = field(default_factory=dict)

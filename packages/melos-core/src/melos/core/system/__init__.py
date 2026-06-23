"""System package exports.

Expose intra-system model types and enums for external use.
"""

from .model import (
    CoordinateDefinition,
    Link,
    Site,
    Joint,
    Geometry,
    RouteNode,
    CableParameters,
    Actuator,
    Sensor,
    CoordinateCoupling,
    SystemModel,
)

from .enums import (
    SystemRole,
    GeometryRole,
    ActuatorKind,
    SensorKind,
    RouteNodeKind,
    JointKind,
    CoordinateKind,
)

from .contact import ContactGeometry, ContactGeometryKind
from melos.core.project.enums import ConnectionKind, InterfaceKind, ConstraintPolicy

__all__ = [
    "CoordinateDefinition",
    "Link",
    "Site",
    "Joint",
    "Geometry",
    "RouteNode",
    "CableParameters",
    "Actuator",
    "Sensor",
    "CoordinateCoupling",
    "SystemModel",
    "SystemRole",
    "GeometryRole",
    "ActuatorKind",
    "SensorKind",
    "RouteNodeKind",
    "JointKind",
    "CoordinateKind",
    "ConnectionKind",
    "InterfaceKind",
    "ConstraintPolicy",
    "ContactGeometry",
    "ContactGeometryKind",
]

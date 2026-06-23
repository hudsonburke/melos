"""System-specific enums extracted from common.enums.

These enums describe roles and kinds used within a single articulated system.
"""

from __future__ import annotations

from enum import StrEnum


class SystemRole(StrEnum):
    """High-level role of a system inside a project."""

    ANATOMICAL = "anatomical"
    DEVICE = "device"
    ENVIRONMENT = "environment"
    SUPPORT = "support"
    CUSTOM = "custom"


class GeometryRole(StrEnum):
    """High-level role of a geometry primitive."""

    VISUAL = "visual"
    COLLISION = "collision"
    WRAP = "wrap"
    CONTACT = "contact"
    FITTING = "fitting"
    CUSTOM = "custom"


class ActuatorKind(StrEnum):
    """Generic actuator categories shared across systems."""

    MOTOR = "motor"
    TORQUE = "torque"
    FORCE = "force"
    POSITION = "position"
    MUSCLE = "muscle"
    CABLE = "cable"
    CUSTOM = "custom"


class SensorKind(StrEnum):
    """Generic sensor categories shared across systems."""

    POSITION = "position"
    VELOCITY = "velocity"
    FORCE = "force"
    TORQUE = "torque"
    IMU = "imu"
    CONTACT = "contact"
    MARKER = "marker"
    CUSTOM = "custom"



class RouteNodeKind(StrEnum):
    """Kind of waypoint in an actuator routing path (cable/tendon/muscle)."""

    SITE = "site"
    WRAP = "wrap"


# Kinematic enums
class JointKind(StrEnum):
    """Backend-neutral joint archetypes."""

    FIXED = "fixed"
    REVOLUTE = "revolute"
    PRISMATIC = "prismatic"
    UNIVERSAL = "universal"
    SPHERICAL = "spherical"
    PLANAR = "planar"
    FREE = "free"
    CUSTOM = "custom"


class CoordinateKind(StrEnum):
    """Type of generalized coordinate associated with a joint."""

    ROTATION = "rotation"
    TRANSLATION = "translation"

"""Enums for the shared articulated-system model and kinematic primitives."""

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


class InterfaceKind(StrEnum):
    """Semantic interface categories used to connect systems."""

    CUFF = "cuff"
    FOOTPLATE = "footplate"
    HARNESS = "harness"
    SOCKET = "socket"
    SOFT_TISSUE_REGION = "soft_tissue_region"
    BONE_ANCHOR_REGION = "bone_anchor_region"
    HAND_GRIP = "hand_grip"
    CUSTOM = "custom"


class ConnectionKind(StrEnum):
    """Kinds of assembly connections between system interfaces."""

    RIGID = "rigid"
    COMPLIANT = "compliant"
    CONTACT_ONLY = "contact_only"
    OBSERVATIONAL = "observational"
    ALIGNMENT_ONLY = "alignment_only"


class ConstraintPolicy(StrEnum):
    """Backend-lowering strategy for a connection."""

    LOWER_TO_WELD = "lower_to_weld"
    LOWER_TO_EQUALITY = "lower_to_equality"
    LOWER_TO_SPRINGS = "lower_to_springs"
    LOWER_TO_CONTACTS = "lower_to_contacts"
    AUTHORING_ONLY = "authoring_only"


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

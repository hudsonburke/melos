"""Enums owned by the shared kinematics subdomain."""

from __future__ import annotations

from enum import StrEnum


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

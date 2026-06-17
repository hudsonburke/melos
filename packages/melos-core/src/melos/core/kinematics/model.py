"""Shared kinematic dataclasses."""

from __future__ import annotations

from dataclasses import dataclass

from enum import StrEnum

from melos.core.common.ids import Identifier
from melos.core.common.types import Bounds, Vec3


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


@dataclass(slots=True, kw_only=True)
class CoordinateDefinition:
    """Named generalized coordinate associated with a joint."""

    id: Identifier
    name: str
    kind: CoordinateKind
    axis: Vec3
    default_value: float = 0.0
    limits: Bounds | None = None
    description: str = ""

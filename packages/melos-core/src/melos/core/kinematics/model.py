"""Shared kinematic dataclasses."""

from __future__ import annotations

from dataclasses import dataclass

from melos.core.common.ids import Identifier
from melos.core.common.types import Bounds, Vec3

from .enums import CoordinateKind


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

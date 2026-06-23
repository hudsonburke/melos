"""Contact geometry model definitions for a single system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from melos.core.common.ids import Identifier
from melos.core.common.types import AnnotationMap, Vec3, Transform, ZERO_VEC3


class ContactGeometryKind(StrEnum):
    """Geometric archetypes used to define contact surfaces."""

    SPHERE = "sphere"
    CAPSULE = "capsule"
    BOX = "box"
    CYLINDER = "cylinder"
    MESH = "mesh"
    PLANE = "plane"


@dataclass(slots=True, kw_only=True)
class ContactGeometry:
    id: Identifier
    name: str
    kind: ContactGeometryKind
    link_id: Identifier | None = None
    site_id: Identifier | None = None
    transform: Transform = field(default_factory=Transform.identity)
    size: Vec3 = ZERO_VEC3
    asset_id: Identifier | None = None
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)

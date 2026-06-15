"""Contact geometry and contact pair model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.ids import Identifier
from melos.core.common.metadata import AnnotationMap
from melos.core.common.types import Vec3, Transform, ZERO_VEC3
from melos.core.contact.enums import ContactGeometryKind, ContactFilterMode


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


@dataclass(slots=True, kw_only=True)
class ContactPair:
    id: Identifier
    name: str
    geom_a_id: Identifier
    geom_b_id: Identifier
    filter_mode: ContactFilterMode = ContactFilterMode.INCLUDE
    friction: tuple[float, ...] | None = None
    solref: tuple[float, float] | None = None
    solimp: tuple[float, float, float] | None = None
    margin: float | None = None
    gap: float | None = None
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)

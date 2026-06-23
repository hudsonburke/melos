"""Attachment schema for connecting meshes to articulated systems."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.enums import InterfaceKind
from melos.core.common.ids import Identifier
from melos.core.common.types import AnnotationMap, Transform


@dataclass(slots=True, kw_only=True)
class AttachmentFit:
    """Fitting metadata that describes how a mesh was registered to a target system."""

    anchor_link_id: Identifier
    rest_transform_in_anchor: Transform
    fit_coordinate_values: dict[Identifier, float]
    reference_link_ids: list[Identifier] = field(default_factory=list)
    reference_site_ids: list[Identifier] = field(default_factory=list)
    reference_geometry_ids: list[Identifier] = field(default_factory=list)
    fit_method: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Attachment:
    """Descriptor for a mesh connected to a target articulated system."""

    id: str
    name: str
    target_system_id: Identifier
    mesh_asset_id: Identifier
    binding_asset_id: Identifier
    interface_kind: InterfaceKind
    fit: AttachmentFit
    translation_map_id: str | None = None
    binding_mode: str = "rigid"
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)

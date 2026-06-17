"""Skin attachment schema for project-level garment/skin binding definitions."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.ids import Identifier
from melos.core.common.types import AnnotationMap, Transform

DEFAULT_SKIN_BINDING_MODE = "link_linear_blend"


@dataclass(slots=True, kw_only=True)
class SkinAttachmentFit:
    """Fitting metadata that describes how a skin mesh was registered to a target system."""

    anchor_link_id: Identifier
    rest_transform_in_anchor: Transform
    fit_coordinate_values: dict[Identifier, float]
    reference_link_ids: list[Identifier] = field(default_factory=list)
    reference_site_ids: list[Identifier] = field(default_factory=list)
    reference_geometry_ids: list[Identifier] = field(default_factory=list)
    fit_method: str = "skin_system_fit_v1"
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class SkinAttachment:
    """Project-level descriptor for a skin mesh bound to a target articulated system."""

    id: str
    name: str
    target_system_id: Identifier
    mesh_asset_id: Identifier
    binding_asset_id: Identifier
    fit: SkinAttachmentFit
    translation_map_id: str | None = None
    binding_mode: str = DEFAULT_SKIN_BINDING_MODE
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)

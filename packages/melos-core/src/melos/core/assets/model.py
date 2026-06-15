"""Asset registry and asset-reference models."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.enums import AssetRole
from melos.core.common.ids import Identifier
from melos.core.common.metadata import AnnotationMap


@dataclass(slots=True, kw_only=True)
class AssetRecord:
    """Asset metadata stored in the project-level asset registry."""

    id: Identifier
    name: str
    role: AssetRole
    uri: str
    media_type: str | None = None
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class AssetLibrary:
    """Container for all asset records referenced by a project."""

    items: list[AssetRecord] = field(default_factory=list)

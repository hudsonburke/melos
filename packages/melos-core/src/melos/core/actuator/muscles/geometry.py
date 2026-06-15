"""Optional geometry and representation metadata for muscle actuators."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.ids import Identifier
from melos.core.common.metadata import AnnotationMap
from melos.core.common.types import Transform
from .enums import (
    MuscleLineOfActionSource,
    MuscleRepresentationKind,
)


@dataclass(slots=True, kw_only=True)
class MuscleGeometry:
    """Optional geometry associated with a muscle.

    This can be used for visualization, fitting, centerline extraction, or
    future volumetric workflows while keeping the canonical path definition
    separate.
    """

    asset_id: Identifier | None = None
    centerline_asset_id: Identifier | None = None
    line_of_action_source: MuscleLineOfActionSource = MuscleLineOfActionSource.PATH_POINTS
    rest_transform: Transform = field(default_factory=Transform.identity)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class MuscleSimulationHints:
    """Optional hints for exporters or runtime backends.

    These are intentionally advisory rather than normative so the canonical
    anatomy model does not become backend-specific.
    """

    preferred_representation: MuscleRepresentationKind = MuscleRepresentationKind.PATH
    volume_asset_id: Identifier | None = None
    notes: str = ""
    annotations: AnnotationMap = field(default_factory=dict)

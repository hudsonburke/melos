from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.ids import LinkId, SystemId
from melos.core.common.metadata import AnnotationMap
from melos.core.common.types import Vec3


@dataclass(slots=True, kw_only=True)
class JointPositionSet:
    """Named joint positions expressed in a declared space and unit system."""

    positions: dict[str, Vec3] = field(default_factory=dict)
    space: str = "world"
    units: str = "m"
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class SegmentMeasurement:
    """A scalar segment length derived from a pair or chain of joints."""

    segment_id: str
    length: float
    source_joint_names: list[str] = field(default_factory=list)
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class SegmentMeasurementSet:
    """Named segment measurements expressed in a declared unit system."""

    items: list[SegmentMeasurement] = field(default_factory=list)
    units: str = "m"
    annotations: AnnotationMap = field(default_factory=dict)

    def as_dict(self) -> dict[str, float]:
        return {item.segment_id: item.length for item in self.items}


@dataclass(slots=True, kw_only=True)
class RetargetBindingSpec:
    """Core binding/retarget layer derived from a canonical articulated system."""

    target_system_id: SystemId | None = None
    deformer_link_ids: list[LinkId] = field(default_factory=list)
    joint_to_link_map: dict[str, LinkId] = field(default_factory=dict)
    anchor_link_id: LinkId | None = None
    reference_link_ids: list[LinkId] = field(default_factory=list)
    annotations: AnnotationMap = field(default_factory=dict)

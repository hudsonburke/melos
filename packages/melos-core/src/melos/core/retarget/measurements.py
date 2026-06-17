from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from melos.core.common.transforms import vec3_length, vec3_sub
from .model import JointPositionSet, SegmentMeasurement, SegmentMeasurementSet


def compute_segment_measurements_from_rules(
    joint_positions: JointPositionSet,
    rules: Iterable[Any],
    *,
    units: str | None = None,
) -> SegmentMeasurementSet:
    """Derive per-segment lengths from a rule set using joint positions.

    Expected rule attributes:
    - segment_id
    - target_joint_ids
    - reduction_mode in {direct, chain_sum, inherit_parent, ignore}
    """

    items: list[SegmentMeasurement] = []
    positions = joint_positions.positions

    for rule in rules:
        segment_id = getattr(rule, "segment_id", None)
        if segment_id is None:
            continue

        joint_names = [str(name) for name in (getattr(rule, "target_joint_ids", ()) or ())]
        reduction_mode = str(getattr(rule, "reduction_mode", "direct") or "direct")

        if reduction_mode in {"ignore", "inherit_parent"}:
            continue
        if len(joint_names) < 2:
            continue
        if any(name not in positions for name in joint_names):
            continue

        if reduction_mode == "chain_sum":
            length = sum(
                vec3_length(vec3_sub(positions[joint_names[index]], positions[joint_names[index + 1]]))
                for index in range(len(joint_names) - 1)
            )
        else:
            length = vec3_length(vec3_sub(positions[joint_names[0]], positions[joint_names[-1]]))

        items.append(
            SegmentMeasurement(
                segment_id=str(segment_id),
                length=length,
                source_joint_names=joint_names,
                annotations={"reduction_mode": reduction_mode},
            )
        )

    return SegmentMeasurementSet(items=items, units=units or joint_positions.units)

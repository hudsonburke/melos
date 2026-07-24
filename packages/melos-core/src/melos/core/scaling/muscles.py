"""Muscle scaling: scale path point positions and physiology lengths."""

from __future__ import annotations

import math

from melos.core.common.types import Vec3
from melos.core.scaling.factors import ScaleFactorMap
from melos.core.muscles.model import (
    MuscleModel,
    MusclePath,
    MusclePathPoint,
    MusclePhysiology,
)


def _scale_position(position: Vec3, scale: float) -> Vec3:
    return (position[0] * scale, position[1] * scale, position[2] * scale)


def _scale_path_point(point: MusclePathPoint, scale_factors: ScaleFactorMap) -> MusclePathPoint:
    if point.link_id is not None and point.link_id in scale_factors:
        scaled_pos = _scale_position(point.position, scale_factors[point.link_id])
    else:
        scaled_pos = point.position

    return MusclePathPoint(
        id=point.id,
        name=point.name,
        kind=point.kind,
        link_id=point.link_id,
        site_id=point.site_id,
        landmark_id=point.landmark_id,
        position=scaled_pos,
        description=point.description,
        annotations=point.annotations,
    )


def _compute_length_scale(points: list[MusclePathPoint], scale_factors: ScaleFactorMap) -> float:
    log_sum = 0.0
    count = 0
    for p in points:
        if p.link_id is not None and p.link_id in scale_factors:
            log_sum += math.log(scale_factors[p.link_id])
            count += 1
    if count == 0:
        return 1.0
    return math.exp(log_sum / count)


def _scale_physiology(physiology: MusclePhysiology, length_scale: float) -> MusclePhysiology:
    return MusclePhysiology(
        max_isometric_force=physiology.max_isometric_force,
        optimal_fiber_length=(
            physiology.optimal_fiber_length * length_scale
            if physiology.optimal_fiber_length is not None
            else None
        ),
        tendon_slack_length=(
            physiology.tendon_slack_length * length_scale
            if physiology.tendon_slack_length is not None
            else None
        ),
        pennation_angle=physiology.pennation_angle,
        specific_tension=physiology.specific_tension,
        description=physiology.description,
    )


def scale_muscles(
    muscles: list[MuscleModel],
    scale_factors: ScaleFactorMap,
) -> list[MuscleModel]:
    """Scale muscle path points and physiology lengths by link scale factors.

    Path point positions are scaled component-wise by their parent link's scale
    factor. Physiological lengths (optimal_fiber_length, tendon_slack_length)
    are scaled by the geometric mean of all link scale factors touched by the
    muscle's path points. Force, pennation angle, and specific tension are
    unchanged. Input objects are not mutated.

    Args:
        muscles: List of MuscleModel instances to scale.
        scale_factors: Mapping from link ID to scalar scale factor.

    Returns:
        A new list of scaled MuscleModel instances.
    """
    result: list[MuscleModel] = []

    for muscle in muscles:
        scaled_points = [_scale_path_point(p, scale_factors) for p in muscle.path.points]

        length_scale = _compute_length_scale(muscle.path.points, scale_factors)

        scaled_path = MusclePath(
            points=scaled_points,
            wrap_geometry_ids=list(muscle.path.wrap_geometry_ids),
            description=muscle.path.description,
            annotations=muscle.path.annotations,
        )

        scaled_physiology: MusclePhysiology | None
        if muscle.physiology is not None:
            scaled_physiology = _scale_physiology(muscle.physiology, length_scale)
        else:
            scaled_physiology = None

        result.append(
            MuscleModel(
                id=muscle.id,
                name=muscle.name,
                path=scaled_path,
                physiology=scaled_physiology,
                description=muscle.description,
                annotations=muscle.annotations,
            )
        )

    return result

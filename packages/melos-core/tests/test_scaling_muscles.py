from __future__ import annotations

import math

import pytest

from melos.core.scaling.muscles import scale_muscles
from melos.core.actuator.muscles.enums import MusclePathPointKind
from melos.core.actuator.muscles.model import (
    MuscleModel,
    MusclePath,
    MusclePathPoint,
    MusclePhysiology,
)


def _make_point(
    point_id: str,
    link_id: str | None,
    position: tuple[float, float, float],
    kind: MusclePathPointKind = MusclePathPointKind.VIA,
) -> MusclePathPoint:
    return MusclePathPoint(
        id=point_id,
        name=point_id,
        kind=kind,
        link_id=link_id,
        position=position,
    )


def _make_muscle(
    muscle_id: str,
    points: list[MusclePathPoint],
    physiology: MusclePhysiology | None = None,
) -> MuscleModel:
    return MuscleModel(
        id=muscle_id,
        name=muscle_id,
        path=MusclePath(points=points),
        physiology=physiology,
    )


def test_single_segment_path_point_scaling():
    point = _make_point("p1", "forearm", (0.01, 0.02, 0.03))
    muscle = _make_muscle("m1", [point])
    scaled = scale_muscles([muscle], {"forearm": 1.5})
    sp = scaled[0].path.points[0]
    assert sp.position == pytest.approx((0.015, 0.03, 0.045))


def test_physiology_fiber_and_tendon_scale():
    point = _make_point("p1", "upper_arm", (0.1, 0.0, 0.0))
    physiology = MusclePhysiology(optimal_fiber_length=0.1, tendon_slack_length=0.2)
    muscle = _make_muscle("m1", [point], physiology)
    scaled = scale_muscles([muscle], {"upper_arm": 2.0})
    phys = scaled[0].physiology
    assert phys is not None
    assert phys.optimal_fiber_length == pytest.approx(0.2)
    assert phys.tendon_slack_length == pytest.approx(0.4)


def test_physiology_force_and_pennation_unchanged():
    point = _make_point("p1", "upper_arm", (0.1, 0.0, 0.0))
    physiology = MusclePhysiology(
        max_isometric_force=1000.0,
        pennation_angle=0.15,
        specific_tension=350000.0,
    )
    muscle = _make_muscle("m1", [point], physiology)
    scaled = scale_muscles([muscle], {"upper_arm": 2.0})
    phys = scaled[0].physiology
    assert phys is not None
    assert phys.max_isometric_force == pytest.approx(1000.0)
    assert phys.pennation_angle == pytest.approx(0.15)
    assert phys.specific_tension == pytest.approx(350000.0)


def test_path_point_with_none_link_id_unchanged():
    point = _make_point("p1", None, (0.05, 0.10, 0.15))
    muscle = _make_muscle("m1", [point])
    scaled = scale_muscles([muscle], {"forearm": 2.0})
    sp = scaled[0].path.points[0]
    assert sp.position == pytest.approx((0.05, 0.10, 0.15))


def test_none_physiology_no_crash():
    point = _make_point("p1", "forearm", (0.1, 0.0, 0.0))
    muscle = _make_muscle("m1", [point], physiology=None)
    scaled = scale_muscles([muscle], {"forearm": 2.0})
    assert scaled[0].physiology is None


def test_multi_segment_muscle_geometric_mean():
    point_a = _make_point("p1", "body_a", (0.1, 0.0, 0.0))
    point_b = _make_point("p2", "body_b", (0.2, 0.0, 0.0))
    physiology = MusclePhysiology(optimal_fiber_length=0.1, tendon_slack_length=0.05)
    muscle = _make_muscle("m1", [point_a, point_b], physiology)
    scaled = scale_muscles([muscle], {"body_a": 2.0, "body_b": 8.0})
    expected_length_scale = math.exp((math.log(2.0) + math.log(8.0)) / 2)
    assert expected_length_scale == pytest.approx(4.0)
    phys = scaled[0].physiology
    assert phys is not None
    assert phys.optimal_fiber_length == pytest.approx(0.1 * 4.0)
    assert phys.tendon_slack_length == pytest.approx(0.05 * 4.0)


def test_input_muscles_not_mutated():
    original_pos = (0.05, 0.10, 0.15)
    point = _make_point("p1", "forearm", original_pos)
    physiology = MusclePhysiology(optimal_fiber_length=0.1, tendon_slack_length=0.2)
    muscle = _make_muscle("m1", [point], physiology)
    _ = scale_muscles([muscle], {"forearm": 3.0})
    assert muscle.path.points[0].position == original_pos
    assert muscle.physiology is not None
    assert muscle.physiology.optimal_fiber_length == pytest.approx(0.1)
    assert muscle.physiology.tendon_slack_length == pytest.approx(0.2)


def test_unmapped_link_id_position_unchanged():
    point = _make_point("p1", "unknown_body", (0.05, 0.10, 0.15))
    muscle = _make_muscle("m1", [point])
    scaled = scale_muscles([muscle], {"forearm": 2.0})
    sp = scaled[0].path.points[0]
    assert sp.position == pytest.approx((0.05, 0.10, 0.15))

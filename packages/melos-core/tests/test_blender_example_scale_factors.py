from __future__ import annotations

import pytest

from melos.blender.addon.operators.project import _compute_example_segment_scale_factors
from melos.core.common.types import Transform
from melos.core.retarget.translation import SegmentTranslationRule, TranslationMap


def test_compute_example_segment_scale_factors_uses_mapped_joint_distances() -> None:
    skin_joints = {
        "Hips": (0.0, 100.0, 0.0),
        "LeftLeg": (-10.0, 90.0, 0.0),
        "LeftShin": (-10.0, 50.0, 0.0),
        "LeftFoot": (-10.0, 8.0, 0.0),
    }
    world_transforms = {
        "pelvis": Transform(translation=(0.0, 1.0, 0.0)),
        "femur_l": Transform(translation=(-0.1, 0.9, 0.0)),
        "tibia_l": Transform(translation=(-0.1, 0.5, 0.0)),
        "talus_l": Transform(translation=(-0.1, 0.1, 0.0)),
    }
    translation_map = TranslationMap(
        id="map",
        source_rig="source",
        target_rig="target",
        version="1",
        rules=[
            SegmentTranslationRule(segment_id="pelvis", source_link_id="pelvis", target_link_id="pelvis", anchor_target_joint_id="Hips"),
            SegmentTranslationRule(segment_id="left_thigh", source_link_id="femur_l", target_link_id="left_thigh", parent_segment_id="pelvis", target_joint_ids=["LeftLeg", "LeftShin"], anchor_target_joint_id="LeftLeg"),
            SegmentTranslationRule(segment_id="left_shank", source_link_id="tibia_l", target_link_id="left_shank", parent_segment_id="left_thigh", target_joint_ids=["LeftShin", "LeftFoot"], anchor_target_joint_id="LeftShin"),
        ],
    )

    factors = _compute_example_segment_scale_factors(skin_joints, world_transforms, translation_map)

    assert factors["left_thigh"] == pytest.approx(0.4 / 40.0)
    assert factors["left_shank"] == pytest.approx(0.4 / 42.0)

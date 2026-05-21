from __future__ import annotations

import pytest

from melos.blender.addon.operators.project import _compute_skin_joint_alignment
from melos.core.common.types import Transform
from melos.core.retarget.translation import SegmentTranslationRule, TranslationMap


def test_compute_skin_joint_alignment_keeps_small_metric_scale() -> None:
    skin_joints = {
        "Hips": (0.0, 100.0, 0.0),
        "Neck1": (0.0, 160.0, 0.0),
        "LeftLeg": (-10.0, 90.0, 0.0),
        "RightLeg": (10.0, 90.0, 0.0),
    }
    world_transforms = {
        "pelvis": Transform(translation=(0.0, 1.0, 0.0)),
        "head": Transform(translation=(0.0, 1.6, 0.0)),
        "femur_l": Transform(translation=(-0.1, 0.9, 0.0)),
        "femur_r": Transform(translation=(0.1, 0.9, 0.0)),
    }
    translation_map = TranslationMap(
        id="map",
        source_rig="source",
        target_rig="target",
        version="1",
        rules=[
            SegmentTranslationRule(segment_id="pelvis", source_link_id="pelvis", target_link_id="pelvis", anchor_target_joint_id="Hips"),
            SegmentTranslationRule(segment_id="head", source_link_id="head", target_link_id="head", anchor_target_joint_id="Head", target_joint_ids=["Neck1", "Head"]),
            SegmentTranslationRule(segment_id="left_thigh", source_link_id="femur_l", target_link_id="left_thigh", anchor_target_joint_id="LeftLeg", target_joint_ids=["LeftLeg"]),
            SegmentTranslationRule(segment_id="right_thigh", source_link_id="femur_r", target_link_id="right_thigh", anchor_target_joint_id="RightLeg", target_joint_ids=["RightLeg"]),
        ],
    )

    alignment = _compute_skin_joint_alignment(skin_joints, world_transforms, translation_map)

    assert alignment["scale"] == pytest.approx(0.01)

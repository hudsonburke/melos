from __future__ import annotations

import pytest

from melos.core.common.types import Transform
from melos.core.retarget import (
    apply_similarity_to_vertices,
    compute_joint_alignment_similarity,
    compute_reference_alignment_similarity,
)
from melos.core.retarget.translation import SegmentTranslationRule, TranslationMap


def test_compute_joint_alignment_similarity_keeps_small_metric_scale() -> None:
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

    alignment = compute_joint_alignment_similarity(skin_joints, world_transforms, translation_map)

    assert alignment["scale"] == pytest.approx(0.01)


def test_compute_reference_alignment_similarity_matches_head_axis() -> None:
    reference_points = {
        "pelvis": (0.0, 0.0, 0.0),
        "head": (0.0, 100.0, 0.0),
        "left_thigh": (-20.0, -20.0, 0.0),
        "right_thigh": (20.0, -20.0, 0.0),
    }
    world_transforms = {
        "pelvis": Transform(translation=(1.0, 2.0, 3.0)),
        "head": Transform(translation=(1.0, 2.0, 4.0)),
        "femur_l": Transform(translation=(0.8, 1.8, 3.0)),
        "femur_r": Transform(translation=(1.2, 1.8, 3.0)),
    }
    translation_map = TranslationMap(
        id="map",
        source_rig="source",
        target_rig="target",
        version="1",
        rules=[
            SegmentTranslationRule(segment_id="pelvis", source_link_id="pelvis", target_link_id="pelvis", anchor_target_joint_id="Hips"),
            SegmentTranslationRule(segment_id="head", source_link_id="head", target_link_id="head", target_joint_ids=["Neck1", "Head"], anchor_target_joint_id="Head"),
            SegmentTranslationRule(segment_id="left_thigh", source_link_id="femur_l", target_link_id="left_thigh", target_joint_ids=["LeftLeg"], anchor_target_joint_id="LeftLeg"),
            SegmentTranslationRule(segment_id="right_thigh", source_link_id="femur_r", target_link_id="right_thigh", target_joint_ids=["RightLeg"], anchor_target_joint_id="RightLeg"),
        ],
    )

    similarity = compute_reference_alignment_similarity(reference_points, world_transforms, translation_map)
    mapped = apply_similarity_to_vertices([[0.0, 0.0, 0.0], [0.0, 100.0, 0.0]], similarity)

    mapped_axis = (
        mapped[1][0] - mapped[0][0],
        mapped[1][1] - mapped[0][1],
        mapped[1][2] - mapped[0][2],
    )
    target_axis = (
        world_transforms["head"].translation[0] - world_transforms["pelvis"].translation[0],
        world_transforms["head"].translation[1] - world_transforms["pelvis"].translation[1],
        world_transforms["head"].translation[2] - world_transforms["pelvis"].translation[2],
    )
    dot = sum(mapped_axis[i] * target_axis[i] for i in range(3))
    mapped_norm = sum(component * component for component in mapped_axis) ** 0.5
    target_norm = sum(component * component for component in target_axis) ** 0.5

    assert mapped_norm > 0.0
    assert target_norm > 0.0
    assert similarity["scale"] > 0.0
    assert dot / (mapped_norm * target_norm) > 0.99

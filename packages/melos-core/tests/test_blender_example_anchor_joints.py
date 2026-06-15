from __future__ import annotations

from melos.blender.addon.operators.project import _rule_body_anchor_joint, _rule_body_tail_joint
from melos.blender.services.example_workflow import (
    _extend_reference_body_points_with_hand_joints,
    _override_example_arm_reference_body_points,
)
from melos.core.retarget.alignment import identity_similarity
from melos.core.retarget.translation import SegmentTranslationRule


def test_rule_body_anchor_joint_prefers_proximal_source_joint() -> None:
    rule = SegmentTranslationRule(
        segment_id="left_upper_arm",
        source_link_id="humerus_l",
        target_link_id="left_upper_arm",
        target_joint_ids=["LeftShoulder", "LeftArm"],
        anchor_target_joint_id="LeftArm",
    )

    assert _rule_body_anchor_joint(rule) == "LeftShoulder"


def test_rule_body_anchor_joint_falls_back_to_anchor_joint() -> None:
    rule = SegmentTranslationRule(
        segment_id="pelvis",
        source_link_id="pelvis",
        target_link_id="pelvis",
        anchor_target_joint_id="Hips",
    )

    assert _rule_body_anchor_joint(rule) == "Hips"


def test_rule_body_tail_joint_prefers_distal_source_joint() -> None:
    rule = SegmentTranslationRule(
        segment_id="left_thigh",
        source_link_id="femur_l",
        target_link_id="left_thigh",
        target_joint_ids=["LeftLeg", "LeftShin"],
        anchor_target_joint_id="LeftLeg",
    )

    assert _rule_body_tail_joint(rule) == "LeftShin"


def test_rule_body_tail_joint_falls_back_to_anchor_joint() -> None:
    rule = SegmentTranslationRule(
        segment_id="pelvis",
        source_link_id="pelvis",
        target_link_id="pelvis",
        anchor_target_joint_id="Hips",
    )

    assert _rule_body_tail_joint(rule) == "Hips"


def test_example_arm_reference_body_point_override_is_noop_for_humerus() -> None:
    anchors = {
        "humerus_l": (0.0, 0.0, 0.0),
        "ulna_l": (10.0, 0.0, 0.0),
        "radius_l": (20.0, 0.0, 0.0),
        "humerus_r": (30.0, 0.0, 0.0),
        "ulna_r": (40.0, 0.0, 0.0),
        "radius_r": (50.0, 0.0, 0.0),
    }
    tail_points = {
        "humerus_l": (0.0, 1.0, 0.0),
        "ulna_l": (10.0, 1.0, 0.0),
        "radius_l": (20.0, 1.0, 0.0),
        "humerus_r": (30.0, 1.0, 0.0),
        "ulna_r": (40.0, 1.0, 0.0),
        "radius_r": (50.0, 1.0, 0.0),
    }
    original_anchors = dict(anchors)
    original_tail_points = dict(tail_points)
    skin_joint_positions = {
        "LeftArm": (1.0, 2.0, 3.0),
        "LeftForeArm": (4.0, 5.0, 6.0),
        "RightArm": (7.0, 8.0, 9.0),
        "RightForeArm": (10.0, 11.0, 12.0),
    }

    _override_example_arm_reference_body_points(
        anchors,
        tail_points,
        skin_joint_positions,
        identity_similarity(),
    )

    assert anchors == original_anchors
    assert tail_points == original_tail_points



def test_example_hand_reference_body_point_extension_updates_metacarpals() -> None:
    anchors = {
        "secondmc_l": (0.0, 0.0, 0.0),
        "thirdmc_l": (0.0, 0.0, 0.0),
        "lunate_l": (0.0, 0.0, 0.0),
    }
    tail_points = {
        "secondmc_l": (0.0, 1.0, 0.0),
        "thirdmc_l": (0.0, 1.0, 0.0),
        "lunate_l": (0.0, 1.0, 0.0),
    }
    skin_joint_positions = {
        "LeftHand": (1.0, 1.0, 1.0),
        "LeftHandMiddle1": (2.0, 2.0, 2.0),
        "LeftHandIndex1": (3.0, 3.0, 3.0),
        "LeftHandIndex2": (4.0, 4.0, 4.0),
        "LeftHandMiddle2": (5.0, 5.0, 5.0),
    }

    _extend_reference_body_points_with_hand_joints(
        anchors,
        tail_points,
        skin_joint_positions,
        identity_similarity(),
    )

    assert anchors["lunate_l"] == (1.0, 1.0, 1.0)
    assert tail_points["lunate_l"] == (2.0, 2.0, 2.0)
    assert anchors["secondmc_l"] == (3.0, 3.0, 3.0)
    assert tail_points["secondmc_l"] == (4.0, 4.0, 4.0)
    assert anchors["thirdmc_l"] == (2.0, 2.0, 2.0)
    assert tail_points["thirdmc_l"] == (5.0, 5.0, 5.0)

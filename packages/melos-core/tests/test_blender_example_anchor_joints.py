from __future__ import annotations

from melos.blender.addon.operators.project import _rule_body_anchor_joint, _rule_body_tail_joint
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

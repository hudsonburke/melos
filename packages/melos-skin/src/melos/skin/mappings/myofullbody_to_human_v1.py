from __future__ import annotations

from melos.core.retarget.translation import SegmentTranslationRule, TranslationMap


MYOFULLBODY_TO_HUMAN_V1 = TranslationMap(
    id="myofullbody_to_human_v1",
    source_rig="myofullbody",
    target_rig="human",
    version="v1",
    rules=[
        SegmentTranslationRule(segment_id="pelvis", source_link_id="pelvis", target_link_id="pelvis", target_joint_ids=["Hips", "Spine1"], anchor_target_joint_id="Hips", reduction_mode="ignore", failure_policy="ignore"),
        SegmentTranslationRule(segment_id="spine", source_link_id="torso", target_link_id="spine", parent_segment_id="pelvis", target_joint_ids=["Hips", "Spine1"], anchor_target_joint_id="Spine1", template_ref_dir=(0.0, 0.0, 1.0)),
        SegmentTranslationRule(segment_id="thorax", source_link_id="thorax", target_link_id="thorax", parent_segment_id="spine", target_joint_ids=["Spine1", "Spine2", "Chest"], anchor_target_joint_id="Chest", reduction_mode="chain_sum", template_ref_dir=(0.0, 0.0, 1.0)),
        SegmentTranslationRule(segment_id="neck", source_link_id="neck", target_link_id="neck", parent_segment_id="thorax", target_joint_ids=["Chest", "Neck1"], anchor_target_joint_id="Neck1", template_ref_dir=(0.0, 0.0, 1.0)),
        SegmentTranslationRule(segment_id="head", source_link_id="head", target_link_id="head", parent_segment_id="neck", target_joint_ids=["Neck1", "Neck2", "Head"], anchor_target_joint_id="Head", reduction_mode="chain_sum", failure_policy="inherit", template_ref_dir=(0.0, 0.0, 1.0)),
        SegmentTranslationRule(segment_id="left_shoulder_girdle", source_link_id="clavicle_l", target_link_id="left_shoulder_girdle", parent_segment_id="thorax", target_joint_ids=["Chest", "LeftShoulder"], anchor_target_joint_id="LeftShoulder", template_ref_dir=(-1.0, 0.0, 0.0)),
        SegmentTranslationRule(segment_id="left_upper_arm", source_link_id="humerus_l", target_link_id="left_upper_arm", parent_segment_id="left_shoulder_girdle", target_joint_ids=["LeftShoulder", "LeftArm"], anchor_target_joint_id="LeftArm", template_ref_dir=(-1.0, 0.0, 0.0)),
        SegmentTranslationRule(segment_id="left_forearm", source_link_id="ulna_l", target_link_id="left_forearm", parent_segment_id="left_upper_arm", target_joint_ids=["LeftArm", "LeftForeArm"], anchor_target_joint_id="LeftForeArm", template_ref_dir=(0.0, 0.0, -1.0)),
        SegmentTranslationRule(segment_id="left_hand", source_link_id="radius_l", target_link_id="left_hand", parent_segment_id="left_forearm", target_joint_ids=["LeftForeArm", "LeftHand"], anchor_target_joint_id="LeftHand", reduction_mode="inherit_parent", failure_policy="inherit", template_ref_dir=(0.0, 0.0, -1.0)),
        SegmentTranslationRule(segment_id="right_shoulder_girdle", source_link_id="clavicle_r", target_link_id="right_shoulder_girdle", parent_segment_id="thorax", target_joint_ids=["Chest", "RightShoulder"], anchor_target_joint_id="RightShoulder", template_ref_dir=(1.0, 0.0, 0.0)),
        SegmentTranslationRule(segment_id="right_upper_arm", source_link_id="humerus_r", target_link_id="right_upper_arm", parent_segment_id="right_shoulder_girdle", target_joint_ids=["RightShoulder", "RightArm"], anchor_target_joint_id="RightArm", template_ref_dir=(1.0, 0.0, 0.0)),
        SegmentTranslationRule(segment_id="right_forearm", source_link_id="ulna_r", target_link_id="right_forearm", parent_segment_id="right_upper_arm", target_joint_ids=["RightArm", "RightForeArm"], anchor_target_joint_id="RightForeArm", template_ref_dir=(0.0, 0.0, -1.0)),
        SegmentTranslationRule(segment_id="right_hand", source_link_id="radius_r", target_link_id="right_hand", parent_segment_id="right_forearm", target_joint_ids=["RightForeArm", "RightHand"], anchor_target_joint_id="RightHand", reduction_mode="inherit_parent", failure_policy="inherit", template_ref_dir=(0.0, 0.0, -1.0)),
        SegmentTranslationRule(segment_id="left_thigh", source_link_id="femur_l", target_link_id="left_thigh", parent_segment_id="pelvis", target_joint_ids=["LeftLeg", "LeftShin"], anchor_target_joint_id="LeftLeg", template_ref_dir=(-0.669, 0.0, -0.743)),
        SegmentTranslationRule(segment_id="left_shank", source_link_id="tibia_l", target_link_id="left_shank", parent_segment_id="left_thigh", target_joint_ids=["LeftShin", "LeftFoot"], anchor_target_joint_id="LeftShin", template_ref_dir=(0.0, 0.0, -1.0)),
        SegmentTranslationRule(segment_id="left_foot", source_link_id="calcn_l", target_link_id="left_foot", parent_segment_id="left_shank", target_joint_ids=["LeftFoot", "LeftToeBase"], anchor_target_joint_id="LeftFoot", failure_policy="inherit", template_ref_dir=(0.0, 0.0, -1.0)),
        SegmentTranslationRule(segment_id="right_thigh", source_link_id="femur_r", target_link_id="right_thigh", parent_segment_id="pelvis", target_joint_ids=["RightLeg", "RightShin"], anchor_target_joint_id="RightLeg", template_ref_dir=(0.669, 0.0, -0.743)),
        SegmentTranslationRule(segment_id="right_shank", source_link_id="tibia_r", target_link_id="right_shank", parent_segment_id="right_thigh", target_joint_ids=["RightShin", "RightFoot"], anchor_target_joint_id="RightShin", template_ref_dir=(0.0, 0.0, -1.0)),
        SegmentTranslationRule(segment_id="right_foot", source_link_id="calcn_r", target_link_id="right_foot", parent_segment_id="right_shank", target_joint_ids=["RightFoot", "RightToeBase"], anchor_target_joint_id="RightFoot", failure_policy="inherit", template_ref_dir=(0.0, 0.0, -1.0)),
    ],
)


def build_myofullbody_translation_map() -> TranslationMap:
    return MYOFULLBODY_TO_HUMAN_V1

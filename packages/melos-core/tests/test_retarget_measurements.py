from __future__ import annotations

import pytest

from melos.core.retarget import JointPositionSet, compute_segment_measurements_from_rules
from melos.core.retarget.translation import SegmentTranslationRule


def test_compute_segment_measurements_from_rules_handles_direct_and_chain_sum() -> None:
    joints = JointPositionSet(
        positions={
            "Hips": (0.0, 0.0, 0.0),
            "Spine1": (0.0, 0.0, 0.1),
            "Spine2": (0.0, 0.0, 0.2),
            "Chest": (0.0, 0.0, 0.35),
            "LeftLeg": (-0.1, 0.0, -0.1),
            "LeftShin": (-0.1, 0.0, -0.5),
        },
        units="m",
    )
    rules = [
        SegmentTranslationRule(
            segment_id="spine",
            source_link_id="torso",
            target_link_id="spine",
            target_joint_ids=["Hips", "Spine1"],
        ),
        SegmentTranslationRule(
            segment_id="thorax",
            source_link_id="thorax",
            target_link_id="thorax",
            target_joint_ids=["Spine1", "Spine2", "Chest"],
            reduction_mode="chain_sum",
        ),
        SegmentTranslationRule(
            segment_id="left_thigh",
            source_link_id="femur_l",
            target_link_id="left_thigh",
            target_joint_ids=["LeftLeg", "LeftShin"],
        ),
    ]

    measurements = compute_segment_measurements_from_rules(joints, rules)
    measurement_map = measurements.as_dict()

    assert measurement_map["spine"] == pytest.approx(0.1)
    assert measurement_map["thorax"] == pytest.approx(0.25)
    assert measurement_map["left_thigh"] == pytest.approx(0.4)

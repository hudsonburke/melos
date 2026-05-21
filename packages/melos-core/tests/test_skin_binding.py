from __future__ import annotations

import pytest

from melos.core.project.skin_binding import (
    build_link_linear_blend_skinning_transforms,
    collapse_joint_weights_to_binding_spec,
    collapse_joint_weights_to_link_weights,
    pose_vertices_with_link_linear_blend,
)
from melos.core.retarget.model import RetargetBindingSpec


def test_collapse_joint_weights_to_link_weights_merges_joint_contributions() -> None:
    weights, indices = collapse_joint_weights_to_link_weights(
        joint_names=["joint_a", "joint_b", "joint_c"],
        weight_data=[0.6, 0.4, 0.5, 0.5, 0.2, 0.8],
        weight_indices=[0, 1, 0, 1, 0, 1],
        weight_indptr=[0, 2, 4, 6],
        joint_to_link_map={
            "joint_a": "link_1",
            "joint_b": "link_1",
            "joint_c": "link_2",
        },
        link_ids=["link_1", "link_2"],
    )

    assert indices[0] == [0, 1]
    assert weights[0][0] == pytest.approx((0.6 + 0.5) / (0.6 + 0.5 + 0.2))
    assert weights[0][1] == pytest.approx(0.2 / (0.6 + 0.5 + 0.2))
    assert indices[1] == [0, 1]
    assert weights[1][0] == pytest.approx((0.4 + 0.5) / (0.4 + 0.5 + 0.8))
    assert weights[1][1] == pytest.approx(0.8 / (0.4 + 0.5 + 0.8))


def test_collapse_joint_weights_to_binding_spec_uses_core_binding_spec() -> None:
    weights, indices = collapse_joint_weights_to_binding_spec(
        joint_names=["joint_a", "joint_b", "joint_c"],
        weight_data=[0.6, 0.4, 0.5, 0.5, 0.2, 0.8],
        weight_indices=[0, 1, 0, 1, 0, 1],
        weight_indptr=[0, 2, 4, 6],
        binding_spec=RetargetBindingSpec(
            target_system_id="anatomical",
            deformer_link_ids=["link_1", "link_2"],
            joint_to_link_map={
                "joint_a": "link_1",
                "joint_b": "link_1",
                "joint_c": "link_2",
            },
            anchor_link_id="link_1",
        ),
    )

    assert indices[0] == [0, 1]
    assert weights[0][0] == pytest.approx((0.6 + 0.5) / (0.6 + 0.5 + 0.2))
    assert weights[0][1] == pytest.approx(0.2 / (0.6 + 0.5 + 0.2))



def test_pose_vertices_with_link_linear_blend_rotates_segment_to_current_direction() -> None:
    skinning_transforms = build_link_linear_blend_skinning_transforms(
        link_ids=["segment"],
        bind_anchors={"segment": (0.0, 0.0, 0.0)},
        bind_tails={"segment": (1.0, 0.0, 0.0)},
        current_anchors={"segment": (0.0, 0.0, 0.0)},
        current_tails={"segment": (0.0, 1.0, 0.0)},
    )

    posed = pose_vertices_with_link_linear_blend(
        [(1.0, 0.0, 0.0)],
        skinning_transforms=skinning_transforms,
        vertex_link_indices=[[0]],
        vertex_link_weights=[[1.0]],
        link_ids=["segment"],
    )

    assert posed[0] == pytest.approx([0.0, 1.0, 0.0], abs=1e-6)


def test_pose_vertices_with_link_linear_blend_uses_weighted_average_for_multiple_links() -> None:
    skinning_transforms = build_link_linear_blend_skinning_transforms(
        link_ids=["left", "right"],
        bind_anchors={"left": (0.0, 0.0, 0.0), "right": (0.0, 0.0, 0.0)},
        bind_tails={"left": (1.0, 0.0, 0.0), "right": (1.0, 0.0, 0.0)},
        current_anchors={"left": (0.0, 0.0, 0.0), "right": (0.0, 0.0, 0.0)},
        current_tails={"left": (0.0, 1.0, 0.0), "right": (0.0, -1.0, 0.0)},
    )

    posed = pose_vertices_with_link_linear_blend(
        [(1.0, 0.0, 0.0)],
        skinning_transforms=skinning_transforms,
        vertex_link_indices=[[0, 1]],
        vertex_link_weights=[[0.5, 0.5]],
        link_ids=["left", "right"],
    )

    assert posed[0] == pytest.approx([0.0, 0.0, 0.0], abs=1e-6)

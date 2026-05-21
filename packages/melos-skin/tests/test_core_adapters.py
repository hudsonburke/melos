from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from melos.core.retarget.alignment import apply_similarity
from melos.sim.mujoco.adapters import (
    build_example_human_mesh_rigging_plan,
    build_example_scale_link_map,
    build_example_system_retarget_binding_spec,
    build_example_target_joint_secondary_directions,
    build_retarget_link_ids_from_translation_map,
)
from melos.skin.adapters import (
    build_example_mhr_skin_bundle,
    build_example_skin_joint_set,
    load_example_skin_reference_bundle,
    measure_example_skin_segments,
)
from melos.skin.mappings.myofullbody_to_human_v1 import build_myofullbody_translation_map


class _FakeTransform:
    def __init__(self, translation: tuple[float, float, float]) -> None:
        self.translation = translation


class _FakeLink:
    def __init__(self, link_id: str) -> None:
        self.id = link_id


class _FakeSystem:
    def __init__(self, link_ids: list[str], *, system_id: str = "anatomical", root_link_id: str = "Full Body") -> None:
        self.id = system_id
        self.root_link_id = root_link_id
        self.links = [_FakeLink(link_id) for link_id in link_ids]


_REFERENCE_BUNDLE_PATH = (
    Path(__file__).resolve().parents[3] / "resources" / "third_party" / "skin" / "SOMA_neutral.npz"
)
_MHR_ASSET_ROOT = _REFERENCE_BUNDLE_PATH.parent


def test_build_example_scale_link_map_includes_shoulder_girdle_segments() -> None:
    scale_link_map = build_example_scale_link_map()

    assert scale_link_map["left_shoulder_girdle"] == (
        "clavicle_l",
        "clavphant_l",
        "scapphant_l",
    )
    assert scale_link_map["right_shoulder_girdle"] == (
        "clavicle_r",
        "clavphant_r",
        "scapphant_r",
    )



def test_build_example_target_joint_secondary_directions_uses_source_link_frames() -> None:
    class _FakeWorldTransform:
        def __init__(self, translation: tuple[float, float, float], rotation: tuple[float, float, float, float]) -> None:
            self.translation = translation
            self.rotation = rotation

    directions = build_example_target_joint_secondary_directions(
        {
            "thorax": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "clavicle_l": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "humerus_l": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "ulna_l": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "radius_l": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "clavicle_r": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "humerus_r": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "ulna_r": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "radius_r": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "neck": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
            "head": _FakeWorldTransform((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
        }
    )

    assert directions["Chest"] == (0.0, 1.0, 0.0)
    assert directions["LeftShoulder"] == (1.0, 0.0, 0.0)
    assert directions["LeftArm"] == (0.0, 0.0, 1.0)
    assert directions["LeftForeArm"] == (0.0, 0.0, 1.0)
    assert directions["RightArm"] == (0.0, 0.0, 1.0)



def test_load_example_skin_reference_bundle_returns_reference_joint_weight_bundle() -> None:
    bundle = load_example_skin_reference_bundle(_REFERENCE_BUNDLE_PATH)

    assert bundle is not None
    assert len(bundle["vertices"]) > 0
    assert len(bundle["faces"]) > 0
    assert len(bundle["joint_names"]) == len(bundle["joint_parent_ids"])



def test_build_example_mhr_skin_bundle_returns_runtime_bundle_when_available() -> None:
    bundle = build_example_mhr_skin_bundle(_MHR_ASSET_ROOT)
    if importlib.util.find_spec("soma") is None:
        assert bundle is None
        return

    assert bundle is not None
    assert bundle["source_model"] == "mhr"
    assert bundle["identity_model_type"] == "mhr"
    assert len(bundle["vertices"]) > 0
    assert len(bundle["faces"]) > 0
    assert len(bundle["joint_names"]) == len(bundle["joint_parent_ids"])



def test_build_retarget_link_ids_from_translation_map_returns_reduced_deformer_links() -> None:
    link_ids = build_retarget_link_ids_from_translation_map(build_myofullbody_translation_map())

    assert link_ids[:6] == ["pelvis", "torso", "thorax", "neck", "head", "clavicle_l"]
    assert "humerus_l" in link_ids
    assert "ulna_l" in link_ids
    assert "radius_l" in link_ids
    assert "femur_l" in link_ids
    assert "tibia_l" in link_ids
    assert "calcn_l" in link_ids
    assert len(link_ids) == len(set(link_ids))



def test_build_example_system_retarget_binding_spec_derives_core_binding_from_system() -> None:
    system = _FakeSystem(
        [
            "pelvis",
            "torso",
            "thorax",
            "neck",
            "head",
            "clavicle_l",
            "humerus_l",
            "ulna_l",
            "radius_l",
            "clavicle_r",
            "humerus_r",
            "ulna_r",
            "radius_r",
            "femur_l",
            "tibia_l",
            "calcn_l",
            "femur_r",
            "tibia_r",
            "calcn_r",
        ]
    )
    translation_map = build_myofullbody_translation_map()

    spec = build_example_system_retarget_binding_spec(
        system,
        ["Hips", "Chest", "LeftShoulder", "LeftArm", "LeftHand", "RightShoulder", "RightHand"],
        translation_map,
    )

    assert spec.target_system_id == "anatomical"
    assert spec.anchor_link_id == "pelvis"
    assert spec.deformer_link_ids[:6] == ["pelvis", "torso", "thorax", "neck", "head", "clavicle_l"]
    assert spec.reference_link_ids == ["thorax", "humerus_l", "humerus_r", "pelvis"]
    assert spec.joint_to_link_map["LeftShoulder"] == "clavicle_l"
    assert spec.joint_to_link_map["LeftHand"] == "radius_l"
    assert spec.annotations["retarget_link_layer"] == "translation_map_source_links_v1"



def test_build_example_human_mesh_rigging_plan_returns_alignment_and_binding_spec() -> None:
    system = _FakeSystem(
        [
            "pelvis",
            "torso",
            "thorax",
            "neck",
            "head",
            "clavicle_l",
            "humerus_l",
            "ulna_l",
            "radius_l",
            "clavicle_r",
            "humerus_r",
            "ulna_r",
            "radius_r",
            "femur_l",
            "tibia_l",
            "calcn_l",
            "femur_r",
            "tibia_r",
            "calcn_r",
        ]
    )
    translation_map = build_myofullbody_translation_map()
    skin_joint_positions = {
        "Hips": (0.0, 0.0, 100.0),
        "Spine1": (0.0, 0.0, 110.0),
        "Chest": (0.0, 0.0, 120.0),
        "Neck1": (0.0, 0.0, 130.0),
        "LeftShoulder": (-20.0, 10.0, 120.0),
        "LeftArm": (-40.0, 10.0, 115.0),
        "RightShoulder": (20.0, 10.0, 120.0),
        "RightArm": (40.0, 10.0, 115.0),
        "LeftLeg": (-10.0, 0.0, 90.0),
        "LeftShin": (-10.0, 0.0, 50.0),
        "LeftFoot": (-10.0, 0.0, 10.0),
        "RightLeg": (10.0, 0.0, 90.0),
        "RightShin": (10.0, 0.0, 50.0),
        "RightFoot": (10.0, 0.0, 10.0),
    }
    world_transforms = {
        "pelvis": _FakeTransform((0.0, 0.0, 1.0)),
        "torso": _FakeTransform((0.0, 0.0, 1.1)),
        "thorax": _FakeTransform((0.0, 0.0, 1.2)),
        "neck": _FakeTransform((0.0, 0.0, 1.3)),
        "head": _FakeTransform((0.0, 0.0, 1.4)),
        "humerus_l": _FakeTransform((-0.4, 0.1, 1.15)),
        "ulna_l": _FakeTransform((-0.6, 0.1, 1.1)),
        "humerus_r": _FakeTransform((0.4, 0.1, 1.15)),
        "ulna_r": _FakeTransform((0.6, 0.1, 1.1)),
        "femur_l": _FakeTransform((-0.1, 0.0, 0.9)),
        "tibia_l": _FakeTransform((-0.1, 0.0, 0.5)),
        "femur_r": _FakeTransform((0.1, 0.0, 0.9)),
        "tibia_r": _FakeTransform((0.1, 0.0, 0.5)),
    }

    plan = build_example_human_mesh_rigging_plan(
        system,
        world_transforms,
        skin_joint_positions,
        translation_map,
    )

    assert plan.binding_spec.target_system_id == "anatomical"
    assert plan.binding_spec.anchor_link_id == "pelvis"
    assert plan.rest_alignment_similarity["scale"] > 0.0
    assert [link.id for link in plan.display_system.links] == plan.binding_spec.deformer_link_ids
    assert plan.display_system.root_link_id == "pelvis"
    assert plan.reference_body_anchors["humerus_l"] == pytest.approx(
        apply_similarity(skin_joint_positions["LeftShoulder"], plan.rest_alignment_similarity)
    )
    assert plan.reference_body_tail_points["humerus_l"] == pytest.approx(
        apply_similarity(skin_joint_positions["LeftArm"], plan.rest_alignment_similarity)
    )
    assert plan.reference_body_anchors["clavicle_l"] == pytest.approx(
        apply_similarity(skin_joint_positions["Chest"], plan.rest_alignment_similarity)
    )
    assert plan.reference_body_tail_points["clavicle_l"] == pytest.approx(
        apply_similarity(skin_joint_positions["LeftShoulder"], plan.rest_alignment_similarity)
    )



def test_build_example_skin_joint_set_and_segment_measurements_return_core_models() -> None:
    skin_bundle = {
        "joints": {
            "LeftShoulder": (-20.0, 10.0, 130.0),
            "LeftArm": (-50.0, 10.0, 120.0),
            "LeftForeArm": (-70.0, 10.0, 115.0),
            "LeftLeg": (-10.0, 0.0, 90.0),
            "LeftShin": (-10.0, 0.0, 50.0),
            "LeftFoot": (-10.0, 0.0, 10.0),
            "LeftToeBase": (10.0, 0.0, 5.0),
        }
    }
    translation_map = build_myofullbody_translation_map()

    joint_set = build_example_skin_joint_set(skin_bundle)
    measurements = measure_example_skin_segments(skin_bundle, translation_map).as_dict()

    assert joint_set.units == "cm"
    assert measurements["left_upper_arm"] == pytest.approx((30.0 ** 2 + 10.0 ** 2) ** 0.5)
    assert measurements["left_forearm"] == pytest.approx((20.0 ** 2 + 5.0 ** 2) ** 0.5)
    assert measurements["left_thigh"] == pytest.approx(40.0)

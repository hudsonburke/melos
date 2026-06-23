from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from melos.core.common.enums import JointKind
from melos.core.retarget.alignment import (
    SimilarityTransform,
    apply_similarity,
    compute_joint_alignment_similarity,
)
from melos.core.retarget.model import RetargetBindingSpec
from melos.core.common.enums import SystemRole
from melos.core.system.model import Joint, SystemModel


@dataclass(frozen=True)
class ExampleHumanMeshRiggingPlan:
    binding_spec: RetargetBindingSpec
    rest_alignment_similarity: SimilarityTransform
    display_system: SystemModel
    reference_body_anchors: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    reference_body_tail_points: dict[str, tuple[float, float, float]] = field(default_factory=dict)



def build_retarget_link_ids_from_translation_map(translation_map: Any) -> list[str]:
    link_ids: list[str] = []
    seen: set[str] = set()
    for rule in getattr(translation_map, "rules", ()) or ():
        link_id = getattr(rule, "source_link_id", None)
        if link_id is None:
            continue
        resolved = str(link_id)
        if not resolved or resolved in seen:
            continue
        seen.add(resolved)
        link_ids.append(resolved)
    return link_ids



def build_example_human_joint_to_link_map(
    joint_names: list[str],
    translation_map: Any | None,
) -> dict[str, str]:
    joint_to_link: dict[str, str] = {
        "Root": "pelvis",
        "HeadEnd": "head",
        "Jaw": "head",
        "LeftEye": "head",
        "RightEye": "head",
        "LeftShoulder": "clavicle_l",
        "RightShoulder": "clavicle_r",
        "LeftHand": "radius_l",
        "RightHand": "radius_r",
        "LeftToeBase": "calcn_l",
        "LeftToeEnd": "calcn_l",
        "RightToeBase": "calcn_r",
        "RightToeEnd": "calcn_r",
    }

    if translation_map is not None:
        for rule in getattr(translation_map, "rules", ()) or ():
            source_link_id = getattr(rule, "source_link_id", None)
            if not source_link_id:
                continue
            anchor_joint = getattr(rule, "anchor_target_joint_id", None)
            if anchor_joint:
                joint_to_link.setdefault(str(anchor_joint), str(source_link_id))
            for joint_name in getattr(rule, "target_joint_ids", ()) or ():
                joint_to_link.setdefault(str(joint_name), str(source_link_id))

    for joint_name in joint_names:
        if joint_name.startswith("LeftHand"):
            joint_to_link.setdefault(joint_name, "radius_l")
        elif joint_name.startswith("RightHand"):
            joint_to_link.setdefault(joint_name, "radius_r")

    return joint_to_link



def build_example_system_retarget_binding_spec(
    system: Any,
    joint_names: list[str],
    translation_map: Any | None,
) -> RetargetBindingSpec:
    system_link_ids = {
        str(link.id)
        for link in (getattr(system, "links", None) or [])
        if getattr(link, "id", None)
    }
    deformer_link_ids = [
        link_id
        for link_id in build_retarget_link_ids_from_translation_map(translation_map)
        if link_id in system_link_ids
    ]
    joint_to_link_map = {
        joint_name: link_id
        for joint_name, link_id in build_example_human_joint_to_link_map(joint_names, translation_map).items()
        if link_id in system_link_ids
    }
    if "pelvis" in system_link_ids:
        anchor_link_id = "pelvis"
    elif getattr(system, "root_link_id", None) in system_link_ids:
        anchor_link_id = str(getattr(system, "root_link_id"))
    else:
        anchor_link_id = deformer_link_ids[0] if deformer_link_ids else None
    reference_link_ids = [
        link_id
        for link_id in ("thorax", "humerus_l", "humerus_r", "pelvis")
        if link_id in system_link_ids
    ]
    return RetargetBindingSpec(
        target_system_id=getattr(system, "id", None),
        deformer_link_ids=deformer_link_ids,
        joint_to_link_map=joint_to_link_map,
        anchor_link_id=anchor_link_id,
        reference_link_ids=reference_link_ids,
        annotations={
            "source": "melos.sim.mujoco.adapters.retarget_skeleton.build_example_system_retarget_binding_spec",
            "retarget_link_layer": "translation_map_source_links_v1",
        },
    )



def _rule_anchor_joint_id(rule: Any) -> str | None:
    target_joint_ids = list(getattr(rule, "target_joint_ids", ()) or ())
    if target_joint_ids:
        return str(target_joint_ids[0])
    anchor_joint = getattr(rule, "anchor_target_joint_id", None)
    if anchor_joint is None:
        return None
    return str(anchor_joint)



def _rule_tail_joint_id(rule: Any) -> str | None:
    # Prefer reference_target_joint_ids for tail points when available.
    # These define the visual reference direction for body segments like
    # the clavicle, where the binding tail (LeftShoulder) differs from the
    # visual reference tail (LeftArm).
    reference_joint_ids = list(getattr(rule, "reference_target_joint_ids", ()) or ())
    if len(reference_joint_ids) >= 2:
        return str(reference_joint_ids[-1])
    target_joint_ids = list(getattr(rule, "target_joint_ids", ()) or ())
    if len(target_joint_ids) >= 2:
        return str(target_joint_ids[-1])
    anchor_joint = getattr(rule, "anchor_target_joint_id", None)
    if anchor_joint is not None:
        return str(anchor_joint)
    if target_joint_ids:
        return str(target_joint_ids[-1])
    return None



def _build_reference_body_points(
    skin_joint_positions: Mapping[str, tuple[float, float, float]],
    translation_map: Any | None,
    similarity: SimilarityTransform,
    valid_link_ids: set[str],
) -> tuple[dict[str, tuple[float, float, float]], dict[str, tuple[float, float, float]]]:
    if translation_map is None:
        return {}, {}

    aligned_joint_positions = {
        str(joint_name): apply_similarity(
            (float(position[0]), float(position[1]), float(position[2])),
            similarity,
        )
        for joint_name, position in skin_joint_positions.items()
    }

    reference_body_anchors: dict[str, tuple[float, float, float]] = {}
    reference_body_tail_points: dict[str, tuple[float, float, float]] = {}
    for rule in getattr(translation_map, "rules", ()) or ():
        source_link_id = getattr(rule, "source_link_id", None)
        if source_link_id is None:
            continue
        link_id = str(source_link_id)
        if link_id not in valid_link_ids:
            continue

        anchor_joint_id = _rule_anchor_joint_id(rule)
        if anchor_joint_id is None or anchor_joint_id not in aligned_joint_positions:
            continue
        head = aligned_joint_positions[anchor_joint_id]
        reference_body_anchors[link_id] = head

        tail_joint_id = _rule_tail_joint_id(rule)
        if tail_joint_id is None or tail_joint_id not in aligned_joint_positions:
            continue
        tail = aligned_joint_positions[tail_joint_id]
        delta = (
            float(tail[0] - head[0]),
            float(tail[1] - head[1]),
            float(tail[2] - head[2]),
        )
        if (delta[0] * delta[0] + delta[1] * delta[1] + delta[2] * delta[2]) > 1e-12:
            reference_body_tail_points[link_id] = tail

    return reference_body_anchors, reference_body_tail_points



def build_example_deformer_display_system(
    system: SystemModel,
    binding_spec: RetargetBindingSpec,
    translation_map: Any | None,
) -> SystemModel:
    deformer_link_ids = [link_id for link_id in binding_spec.deformer_link_ids]
    link_set = set(deformer_link_ids)
    link_by_id = {
        str(link.id): link
        for link in (getattr(system, "links", None) or [])
        if getattr(link, "id", None) is not None
    }
    display_links = [link_by_id[link_id] for link_id in deformer_link_ids if link_id in link_by_id]

    parent_by_link: dict[str, str] = {}
    if translation_map is not None:
        rule_by_segment_id = {
            str(getattr(rule, "segment_id", "")): rule
            for rule in getattr(translation_map, "rules", ()) or ()
            if getattr(rule, "segment_id", None) is not None
        }
        for rule in getattr(translation_map, "rules", ()) or ():
            source_link_id = getattr(rule, "source_link_id", None)
            parent_segment_id = getattr(rule, "parent_segment_id", None)
            if source_link_id is None or parent_segment_id is None:
                continue
            child_link_id = str(source_link_id)
            if child_link_id not in link_set:
                continue
            parent_rule = rule_by_segment_id.get(str(parent_segment_id))
            if parent_rule is None or getattr(parent_rule, "source_link_id", None) is None:
                continue
            parent_link_id = str(getattr(parent_rule, "source_link_id"))
            if parent_link_id in link_set and parent_link_id != child_link_id:
                parent_by_link[child_link_id] = parent_link_id

    for joint in getattr(system, "joints", None) or []:
        child_link_id = getattr(joint, "child_link_id", None)
        parent_link_id = getattr(joint, "parent_link_id", None)
        if child_link_id is None or parent_link_id is None:
            continue
        child_link_id = str(child_link_id)
        parent_link_id = str(parent_link_id)
        if child_link_id in link_set and parent_link_id in link_set and child_link_id not in parent_by_link:
            parent_by_link[child_link_id] = parent_link_id

    root_link_id = binding_spec.anchor_link_id if binding_spec.anchor_link_id in link_set else None
    if root_link_id is None:
        for link_id in deformer_link_ids:
            if link_id not in parent_by_link:
                root_link_id = link_id
                break

    display_joints = [
        Joint(
            id=f"display_{parent_link_id}__{child_link_id}",
            name=f"display_{parent_link_id}__{child_link_id}",
            kind=JointKind.FIXED,
            parent_link_id=parent_link_id,
            child_link_id=child_link_id,
            parent_site_id=None,
            child_site_id=None,
            coordinates=[],
            description="",
            annotations={"source": "melos.sim.mujoco.adapters.retarget_skeleton.build_example_deformer_display_system"},
        )
        for child_link_id, parent_link_id in parent_by_link.items()
        if child_link_id in link_set and parent_link_id in link_set
    ]

    system_id = str(getattr(system, "id", "anatomical"))
    system_name = str(getattr(system, "name", system_id))
    system_role = getattr(system, "role", None) or SystemRole.CUSTOM
    system_description = str(getattr(system, "description", ""))
    system_asset_ids = list(getattr(system, "asset_ids", ()) or ())
    system_annotations = dict(getattr(system, "annotations", {}) or {})

    return SystemModel(
        id=f"{system_id}_deformer_display",
        name=f"{system_name} Deformer Display",
        role=system_role,
        root_link_id=root_link_id,
        description=system_description,
        asset_ids=system_asset_ids,
        links=list(display_links),
        joints=display_joints,
        sites=[],
        geometries=[],
        actuators=[],
        sensors=[],
        annotations=system_annotations,
    )



def build_example_human_mesh_rigging_plan(
    system: SystemModel,
    world_transforms: Mapping[str, Any],
    skin_joint_positions: Mapping[str, tuple[float, float, float]],
    translation_map: Any | None,
) -> ExampleHumanMeshRiggingPlan:
    binding_spec = build_example_system_retarget_binding_spec(
        system,
        list(skin_joint_positions.keys()),
        translation_map,
    )
    rest_alignment_similarity = compute_joint_alignment_similarity(
        skin_joint_positions,
        world_transforms,
        translation_map,
    )
    reference_body_anchors, reference_body_tail_points = _build_reference_body_points(
        skin_joint_positions,
        translation_map,
        rest_alignment_similarity,
        set(binding_spec.deformer_link_ids),
    )
    return ExampleHumanMeshRiggingPlan(
        binding_spec=binding_spec,
        rest_alignment_similarity=rest_alignment_similarity,
        display_system=build_example_deformer_display_system(system, binding_spec, translation_map),
        reference_body_anchors=reference_body_anchors,
        reference_body_tail_points=reference_body_tail_points,
    )

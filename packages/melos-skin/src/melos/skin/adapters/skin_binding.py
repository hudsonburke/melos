from __future__ import annotations

import math
from typing import Mapping, Sequence

from melos.core.common.transforms import (
    axis_angle_to_quat as _axis_angle_to_quat,
    multiply_quaternions,
    normalize_quaternion_or_identity,
    rotate_vector,
    vec3_add,
    vec3_cross,
    vec3_dot,
    vec3_length,
    vec3_normalize,
    vec3_scale,
    vec3_sub,
)
from melos.core.common.types import Quat, Transform, Vec3
from melos.core.retarget.model import RetargetBindingSpec


def collapse_joint_weights_to_link_weights(
    *,
    joint_names: Sequence[str],
    weight_data: Sequence[float],
    weight_indices: Sequence[int],
    weight_indptr: Sequence[int],
    joint_to_link_map: Mapping[str, str],
    link_ids: Sequence[str],
    max_influences: int = 4,
) -> tuple[list[list[float]], list[list[int]]]:
    """Collapse sparse joint weights onto target link IDs.

    The sparse inputs use the same column-major layout as the reference skin bundle:
    for each joint index, the items between ``weight_indptr[i]`` and
    ``weight_indptr[i + 1]`` provide vertex indices and weights influenced by
    that joint. We aggregate all joint contributions that map to the same link,
    then keep the strongest ``max_influences`` per vertex.
    """

    link_index_by_id = {link_id: index for index, link_id in enumerate(link_ids)}
    vertex_count = 0
    if weight_indices:
        vertex_count = max(int(index) for index in weight_indices) + 1
    vertex_link_weights: list[dict[int, float]] = [dict() for _ in range(vertex_count)]

    for joint_index, joint_name in enumerate(joint_names):
        link_id = joint_to_link_map.get(joint_name)
        link_index = link_index_by_id.get(link_id or "")
        if link_index is None:
            continue
        start = int(weight_indptr[joint_index])
        end = int(weight_indptr[joint_index + 1])
        for item_index in range(start, end):
            vertex_index = int(weight_indices[item_index])
            weight = float(weight_data[item_index])
            if weight <= 0.0:
                continue
            accum = vertex_link_weights[vertex_index]
            accum[link_index] = accum.get(link_index, 0.0) + weight

    collapsed_weights: list[list[float]] = []
    collapsed_indices: list[list[int]] = []
    fallback_index = 0
    for per_vertex in vertex_link_weights:
        if not per_vertex:
            collapsed_weights.append([1.0])
            collapsed_indices.append([fallback_index])
            continue
        sorted_items = sorted(per_vertex.items(), key=lambda item: item[1], reverse=True)[:max_influences]
        total = sum(weight for _, weight in sorted_items)
        if total <= 1e-8:
            collapsed_weights.append([1.0])
            collapsed_indices.append([fallback_index])
            continue
        collapsed_indices.append([index for index, _ in sorted_items])
        collapsed_weights.append([weight / total for _, weight in sorted_items])
    return collapsed_weights, collapsed_indices


def collapse_joint_weights_to_binding_spec(
    *,
    joint_names: Sequence[str],
    weight_data: Sequence[float],
    weight_indices: Sequence[int],
    weight_indptr: Sequence[int],
    binding_spec: RetargetBindingSpec,
    max_influences: int = 4,
) -> tuple[list[list[float]], list[list[int]]]:
    """Collapse sparse joint weights using a canonical retarget binding spec."""

    return collapse_joint_weights_to_link_weights(
        joint_names=joint_names,
        weight_data=weight_data,
        weight_indices=weight_indices,
        weight_indptr=weight_indptr,
        joint_to_link_map=binding_spec.joint_to_link_map,
        link_ids=binding_spec.deformer_link_ids,
        max_influences=max_influences,
    )



def build_link_linear_blend_skinning_transforms(
    *,
    link_ids: Sequence[str],
    bind_anchors: Mapping[str, Vec3],
    bind_tails: Mapping[str, Vec3],
    current_anchors: Mapping[str, Vec3],
    current_tails: Mapping[str, Vec3],
) -> dict[str, Transform]:
    """Build per-link delta transforms from bind segment directions to current ones."""

    transforms: dict[str, Transform] = {}
    for link_id in link_ids:
        bind_anchor = bind_anchors.get(link_id)
        current_anchor = current_anchors.get(link_id)
        if bind_anchor is None or current_anchor is None:
            transforms[link_id] = Transform.identity()
            continue
        bind_tail = bind_tails.get(link_id, bind_anchor)
        current_tail = current_tails.get(link_id, current_anchor)
        rotation = quaternion_from_to(vec3_sub(bind_tail, bind_anchor), vec3_sub(current_tail, current_anchor))
        translation = vec3_sub(current_anchor, rotate_vector(rotation, bind_anchor))
        transforms[link_id] = Transform(translation=translation, rotation=rotation)
    return transforms


def pose_vertices_with_link_linear_blend(
    rest_vertices: Sequence[Sequence[float]],
    *,
    skinning_transforms: Mapping[str, Transform],
    vertex_link_indices: Sequence[Sequence[int]],
    vertex_link_weights: Sequence[Sequence[float]],
    link_ids: Sequence[str],
) -> list[list[float]]:
    """Pose mesh vertices using link-linear-blend skinning transforms."""

    posed_vertices: list[list[float]] = []
    for vertex, index_row, weight_row in zip(rest_vertices, vertex_link_indices, vertex_link_weights):
        bind_vertex = (float(vertex[0]), float(vertex[1]), float(vertex[2]))
        accum = (0.0, 0.0, 0.0)
        total_weight = 0.0
        for link_index, weight in zip(index_row, weight_row):
            if weight <= 0.0 or link_index < 0 or link_index >= len(link_ids):
                continue
            transform = skinning_transforms.get(link_ids[link_index], Transform.identity())
            transformed = vec3_add(rotate_vector(transform.rotation, bind_vertex), transform.translation)
            accum = (
                accum[0] + transformed[0] * float(weight),
                accum[1] + transformed[1] * float(weight),
                accum[2] + transformed[2] * float(weight),
            )
            total_weight += float(weight)
        if total_weight > 1e-8:
            posed_vertices.append([accum[0] / total_weight, accum[1] / total_weight, accum[2] / total_weight])
        else:
            posed_vertices.append([bind_vertex[0], bind_vertex[1], bind_vertex[2]])
    return posed_vertices


def quaternion_from_to(source: Vec3, target: Vec3) -> Quat:
    source_n = vec3_normalize(source)
    target_n = vec3_normalize(target)
    if vec3_length(source_n) < 1e-8 or vec3_length(target_n) < 1e-8:
        return Transform.identity().rotation
    axis = vec3_cross(source_n, target_n)
    axis_length = vec3_length(axis)
    d = max(-1.0, min(1.0, vec3_dot(source_n, target_n)))
    if axis_length < 1e-8:
        if d > 0.0:
            return Transform.identity().rotation
        fallback_axis = _orthogonal_axis(source_n)
        return _axis_angle_to_quat(fallback_axis, math.pi)
    axis = vec3_scale(axis, 1.0 / axis_length)
    angle = math.acos(d)
    return _axis_angle_to_quat(axis, angle)


def _orthogonal_axis(vector: Vec3) -> Vec3:
    if abs(vector[0]) < abs(vector[1]):
        candidate = (1.0, 0.0, 0.0)
    else:
        candidate = (0.0, 1.0, 0.0)
    return vec3_normalize(vec3_cross(vector, candidate))

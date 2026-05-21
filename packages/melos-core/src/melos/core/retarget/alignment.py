from __future__ import annotations

import math
from typing import Any, Mapping, TypedDict

from melos.core.common.types import Vec3


class SimilarityTransform(TypedDict):
    rotation: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
    scale: float
    translation: tuple[float, float, float]


_DEFAULT_JOINT_ALIGNMENT_MAP: dict[str, str] = {
    "pelvis": "Hips",
    "spine": "Spine1",
    "thorax": "Spine1",
    "neck": "Chest",
    "head": "Neck1",
    "left_upper_arm": "LeftShoulder",
    "left_forearm": "LeftArm",
    "right_upper_arm": "RightShoulder",
    "right_forearm": "RightArm",
    "left_thigh": "LeftLeg",
    "left_shank": "LeftShin",
    "left_foot": "LeftFoot",
    "right_thigh": "RightLeg",
    "right_shank": "RightShin",
    "right_foot": "RightFoot",
}

_DEFAULT_TARGET_ALIGNMENT_MAP: dict[str, str] = {
    "pelvis": "pelvis",
    "spine": "torso",
    "thorax": "thorax",
    "neck": "neck",
    "head": "head",
    "left_upper_arm": "humerus_l",
    "left_forearm": "ulna_l",
    "right_upper_arm": "humerus_r",
    "right_forearm": "ulna_r",
    "left_thigh": "femur_l",
    "left_shank": "tibia_l",
    "right_thigh": "femur_r",
    "right_shank": "tibia_r",
}

_DEFAULT_LANDMARK_SEGMENTS: dict[str, str] = {
    "pelvis": "pelvis",
    "head": "head",
    "left_thigh": "left_thigh",
    "right_thigh": "right_thigh",
}


def compute_joint_alignment_similarity(
    joint_positions: Mapping[str, Vec3],
    world_transforms: Mapping[str, Any],
    translation_map: Any | None,
    *,
    default_joint_map: Mapping[str, str] | None = None,
    default_target_map: Mapping[str, str] | None = None,
) -> SimilarityTransform:
    source_points = mapped_joint_alignment_points(
        joint_positions,
        translation_map,
        default_joint_map=default_joint_map,
    )
    target_points = target_alignment_points(
        world_transforms,
        translation_map,
        default_target_map=default_target_map,
    )
    source_landmarks, target_landmarks = point_landmarks(source_points, target_points)
    body_frame_similarity = solve_body_frame_similarity(source_landmarks, target_landmarks)
    if body_frame_similarity is not None:
        return body_frame_similarity
    return solve_axis_aligned_similarity(source_points, target_points)


def compute_reference_alignment_similarity(
    reference_points: Mapping[str, Vec3],
    world_transforms: Mapping[str, Any],
    translation_map: Any | None,
    *,
    landmark_segments: Mapping[str, str] | None = None,
    default_target_map: Mapping[str, str] | None = None,
) -> SimilarityTransform:
    source_landmarks, target_landmarks = body_frame_landmarks(
        reference_points,
        world_transforms,
        translation_map,
        landmark_segments=landmark_segments,
        default_target_map=default_target_map,
    )
    body_frame_similarity = solve_body_frame_similarity(source_landmarks, target_landmarks)
    if body_frame_similarity is not None:
        return body_frame_similarity
    target_points = target_alignment_points(
        world_transforms,
        translation_map,
        default_target_map=default_target_map,
    )
    return solve_axis_aligned_similarity(dict(reference_points), target_points)


def mapped_joint_alignment_points(
    joint_positions: Mapping[str, Vec3],
    translation_map: Any | None,
    *,
    default_joint_map: Mapping[str, str] | None = None,
) -> dict[str, Vec3]:
    if translation_map is None:
        joint_map = default_joint_map or _DEFAULT_JOINT_ALIGNMENT_MAP
        return {
            link_id: joint_positions[joint_name]
            for link_id, joint_name in joint_map.items()
            if joint_name in joint_positions
        }

    return {
        rule.target_link_id: joint_positions[joint_name]
        for rule in translation_map.rules
        if (joint_name := _rule_anchor_joint(rule)) is not None and joint_name in joint_positions
    }


def target_alignment_points(
    world_transforms: Mapping[str, Any],
    translation_map: Any | None,
    *,
    default_target_map: Mapping[str, str] | None = None,
) -> dict[str, Vec3]:
    if translation_map is None:
        target_map = default_target_map or _DEFAULT_TARGET_ALIGNMENT_MAP
        return {
            source_id: _translation_of(world_transforms[target_id])
            for source_id, target_id in target_map.items()
            if target_id in world_transforms
        }
    return {
        rule.target_link_id: _translation_of(world_transforms[rule.source_link_id])
        for rule in translation_map.rules
        if rule.source_link_id in world_transforms
        and (getattr(rule, "target_joint_ids", ()) or getattr(rule, "anchor_target_joint_id", None) is not None)
    }


def point_landmarks(
    source_points: Mapping[str, Vec3],
    target_points: Mapping[str, Vec3],
    *,
    landmark_segments: Mapping[str, str] | None = None,
) -> tuple[dict[str, Vec3], dict[str, Vec3]]:
    landmark_map = landmark_segments or _DEFAULT_LANDMARK_SEGMENTS
    source_landmarks: dict[str, Vec3] = {}
    target_landmarks: dict[str, Vec3] = {}
    for landmark_name, segment_id in landmark_map.items():
        source_point = source_points.get(segment_id)
        target_point = target_points.get(segment_id)
        if source_point is None or target_point is None:
            continue
        source_landmarks[landmark_name] = source_point
        target_landmarks[landmark_name] = target_point
    return source_landmarks, target_landmarks


def body_frame_landmarks(
    reference_points: Mapping[str, Vec3],
    world_transforms: Mapping[str, Any],
    translation_map: Any | None,
    *,
    landmark_segments: Mapping[str, str] | None = None,
    default_target_map: Mapping[str, str] | None = None,
) -> tuple[dict[str, Vec3], dict[str, Vec3]]:
    if translation_map is None:
        target_points = target_alignment_points(
            world_transforms,
            translation_map,
            default_target_map=default_target_map,
        )
        return point_landmarks(reference_points, target_points, landmark_segments=landmark_segments)

    landmark_map = landmark_segments or _DEFAULT_LANDMARK_SEGMENTS
    rules_by_target = {rule.target_link_id: rule for rule in translation_map.rules}
    source_points: dict[str, Vec3] = {}
    target_points: dict[str, Vec3] = {}
    for landmark_name, target_link_id in landmark_map.items():
        rule = rules_by_target.get(target_link_id)
        if rule is None:
            continue
        source_point = reference_points.get(target_link_id)
        target_transform = world_transforms.get(rule.source_link_id)
        if source_point is None or target_transform is None:
            continue
        source_points[landmark_name] = source_point
        target_points[landmark_name] = _translation_of(target_transform)
    return source_points, target_points


def solve_axis_aligned_similarity(
    source_points: Mapping[str, Vec3],
    target_points: Mapping[str, Vec3],
) -> SimilarityTransform:
    common = [key for key in source_points if key in target_points]
    if not common:
        return identity_similarity()

    source = [source_points[key] for key in common]
    target = [target_points[key] for key in common]
    source_centroid = centroid(source)
    target_centroid = centroid(target)
    centered_source = [sub(point, source_centroid) for point in source]
    centered_target = [sub(point, target_centroid) for point in target]
    rotation = solve_rotation_kabsch(centered_source, centered_target)
    rotated_source = [apply_rotation(point, rotation) for point in centered_source]
    source_energy = sum(dot(point, point) for point in centered_source)
    if source_energy > 1e-8:
        raw_scale = sum(dot(rotated_source[i], centered_target[i]) for i in range(len(centered_source))) / source_energy
        scale = raw_scale if raw_scale > 1e-8 else 1.0
    else:
        scale = 1.0
    rotated_centroid = apply_rotation(source_centroid, rotation)
    translation = (
        target_centroid[0] - rotated_centroid[0] * scale,
        target_centroid[1] - rotated_centroid[1] * scale,
        target_centroid[2] - rotated_centroid[2] * scale,
    )
    return {"rotation": rotation, "scale": scale, "translation": translation}


def solve_body_frame_similarity(
    source_points: Mapping[str, Vec3],
    target_points: Mapping[str, Vec3],
) -> SimilarityTransform | None:
    required = tuple(_DEFAULT_LANDMARK_SEGMENTS)
    if any(key not in source_points or key not in target_points for key in required):
        return None

    rotation = solve_body_frame_rotation(source_points, target_points)
    common = [key for key in source_points if key in target_points]
    if not common:
        return None

    source = [source_points[key] for key in common]
    target = [target_points[key] for key in common]
    source_centroid = centroid(source)
    target_centroid = centroid(target)
    centered_source = [sub(point, source_centroid) for point in source]
    centered_target = [sub(point, target_centroid) for point in target]
    rotated_source = [apply_rotation(point, rotation) for point in centered_source]
    source_energy = sum(dot(point, point) for point in centered_source)
    if source_energy > 1e-8:
        raw_scale = sum(dot(rotated_source[i], centered_target[i]) for i in range(len(centered_source))) / source_energy
        scale = raw_scale if raw_scale > 1e-8 else 1.0
    else:
        scale = 1.0
    translation = sub(target_centroid, scale_vec(apply_rotation(source_centroid, rotation), scale))
    return {"rotation": rotation, "scale": scale, "translation": translation}


def solve_body_frame_rotation(
    source_points: Mapping[str, Vec3],
    target_points: Mapping[str, Vec3],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    source_basis = frame_basis(source_points)
    target_basis = frame_basis(target_points)
    return matmul(target_basis, transpose(source_basis))


def frame_basis(
    points: Mapping[str, Vec3],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    longitudinal = normalize(sub(points["head"], points["pelvis"]))
    lateral = normalize(sub(points["left_thigh"], points["right_thigh"]))
    forward = normalize(cross(lateral, longitudinal))
    if length(forward) < 1e-8:
        return identity_similarity()["rotation"]
    lateral = normalize(cross(longitudinal, forward))
    return matrix_from_columns(lateral, forward, longitudinal)


def apply_similarity(point: Vec3, similarity: SimilarityTransform) -> Vec3:
    rotated = apply_rotation(point, similarity["rotation"])
    return (
        rotated[0] * similarity["scale"] + similarity["translation"][0],
        rotated[1] * similarity["scale"] + similarity["translation"][1],
        rotated[2] * similarity["scale"] + similarity["translation"][2],
    )


def apply_similarity_to_vertices(
    vertices: list[list[float]] | list[tuple[float, float, float]],
    similarity: SimilarityTransform,
) -> list[list[float]]:
    return [
        list(apply_similarity((float(vertex[0]), float(vertex[1]), float(vertex[2])), similarity))
        for vertex in vertices
    ]


def identity_similarity() -> SimilarityTransform:
    return {
        "rotation": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "scale": 1.0,
        "translation": (0.0, 0.0, 0.0),
    }


def solve_rotation_kabsch(
    source_points: list[Vec3],
    target_points: list[Vec3],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    if len(source_points) < 3 or len(target_points) < 3:
        return identity_similarity()["rotation"]

    sxx = sxy = sxz = syx = syy = syz = szx = szy = szz = 0.0
    for source, target in zip(source_points, target_points):
        sxx += source[0] * target[0]
        sxy += source[0] * target[1]
        sxz += source[0] * target[2]
        syx += source[1] * target[0]
        syy += source[1] * target[1]
        syz += source[1] * target[2]
        szx += source[2] * target[0]
        szy += source[2] * target[1]
        szz += source[2] * target[2]

    k = (
        (sxx + syy + szz, syz - szy, szx - sxz, sxy - syx),
        (syz - szy, sxx - syy - szz, sxy + syx, szx + sxz),
        (szx - sxz, sxy + syx, -sxx + syy - szz, syz + szy),
        (sxy - syx, szx + sxz, syz + szy, -sxx - syy + szz),
    )

    quaternion = dominant_eigenvector_4x4(k)
    return quat_to_matrix(quaternion)


def dominant_eigenvector_4x4(
    matrix: tuple[
        tuple[float, float, float, float],
        tuple[float, float, float, float],
        tuple[float, float, float, float],
        tuple[float, float, float, float],
    ],
) -> tuple[float, float, float, float]:
    vector = (1.0, 0.0, 0.0, 0.0)
    for _ in range(32):
        next_vector = (
            sum(matrix[0][j] * vector[j] for j in range(4)),
            sum(matrix[1][j] * vector[j] for j in range(4)),
            sum(matrix[2][j] * vector[j] for j in range(4)),
            sum(matrix[3][j] * vector[j] for j in range(4)),
        )
        norm = math.sqrt(sum(component * component for component in next_vector))
        if norm < 1e-10:
            return (1.0, 0.0, 0.0, 0.0)
        vector = (
            next_vector[0] / norm,
            next_vector[1] / norm,
            next_vector[2] / norm,
            next_vector[3] / norm,
        )
    if vector[0] < 0.0:
        return (-vector[0], -vector[1], -vector[2], -vector[3])
    return vector


def quat_to_matrix(
    quaternion: tuple[float, float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    w, x, y, z = quaternion
    return (
        (1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)),
        (2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)),
        (2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)),
    )


def apply_rotation(
    point: Vec3,
    rotation: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
) -> Vec3:
    return (
        rotation[0][0] * point[0] + rotation[0][1] * point[1] + rotation[0][2] * point[2],
        rotation[1][0] * point[0] + rotation[1][1] * point[1] + rotation[1][2] * point[2],
        rotation[2][0] * point[0] + rotation[2][1] * point[1] + rotation[2][2] * point[2],
    )


def centroid(points: list[Vec3]) -> Vec3:
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
        sum(point[2] for point in points) / len(points),
    )


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length(v: Vec3) -> float:
    return math.sqrt(dot(v, v))


def normalize(v: Vec3) -> Vec3:
    magnitude = length(v)
    if magnitude < 1e-8:
        return (0.0, 0.0, 0.0)
    return (v[0] / magnitude, v[1] / magnitude, v[2] / magnitude)


def scale_vec(v: Vec3, scalar: float) -> Vec3:
    return (v[0] * scalar, v[1] * scalar, v[2] * scalar)


def transpose(
    matrix: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return (
        (matrix[0][0], matrix[1][0], matrix[2][0]),
        (matrix[0][1], matrix[1][1], matrix[2][1]),
        (matrix[0][2], matrix[1][2], matrix[2][2]),
    )


def matmul(
    left: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
    right: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return (
        (
            left[0][0] * right[0][0] + left[0][1] * right[1][0] + left[0][2] * right[2][0],
            left[0][0] * right[0][1] + left[0][1] * right[1][1] + left[0][2] * right[2][1],
            left[0][0] * right[0][2] + left[0][1] * right[1][2] + left[0][2] * right[2][2],
        ),
        (
            left[1][0] * right[0][0] + left[1][1] * right[1][0] + left[1][2] * right[2][0],
            left[1][0] * right[0][1] + left[1][1] * right[1][1] + left[1][2] * right[2][1],
            left[1][0] * right[0][2] + left[1][1] * right[1][2] + left[1][2] * right[2][2],
        ),
        (
            left[2][0] * right[0][0] + left[2][1] * right[1][0] + left[2][2] * right[2][0],
            left[2][0] * right[0][1] + left[2][1] * right[1][1] + left[2][2] * right[2][1],
            left[2][0] * right[0][2] + left[2][1] * right[1][2] + left[2][2] * right[2][2],
        ),
    )


def matrix_from_columns(
    col0: Vec3,
    col1: Vec3,
    col2: Vec3,
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return (
        (col0[0], col1[0], col2[0]),
        (col0[1], col1[1], col2[1]),
        (col0[2], col1[2], col2[2]),
    )


def _translation_of(transform_like: Any) -> Vec3:
    translation = getattr(transform_like, "translation", transform_like)
    return (float(translation[0]), float(translation[1]), float(translation[2]))


def _rule_anchor_joint(rule: Any) -> str | None:
    target_joint_ids = list(getattr(rule, "target_joint_ids", ()) or ())
    if target_joint_ids:
        return str(target_joint_ids[0])
    anchor_joint = getattr(rule, "anchor_target_joint_id", None)
    if anchor_joint is None:
        return None
    return str(anchor_joint)

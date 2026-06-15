from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from melos.blender.bpy_io.skinned_import import compute_project_link_world_transforms, rotate_vector_by_quaternion
from melos.core.retarget import (
    SimilarityTransform,
    compute_joint_alignment_similarity,
    compute_reference_alignment_similarity,
)
from melos.core.scaling import (
    fit_project_system_to_measurements,
    link_scale_factors_from_segment_scale_factors,
)
from melos.sim.mujoco.adapters.example_source import (
    build_example_scale_link_map,
    build_example_visual_scale_link_map,
    example_source_segment_length,
    measure_example_source_segments,
    refine_target_joints_from_source_visuals as refine_target_joints_from_source_visuals_from_source,
)
from melos.sim.mujoco.importers import import_mjcf
from melos.skin.adapters.skin_bundle import measure_example_skin_segments


_REPO_ROOT = Path(__file__).resolve().parents[6]


EXAMPLE_KINEMATIC_SCALE_LINKS: dict[str, tuple[str, ...]] = {
    "head": ("head",),
    "left_upper_arm": ("ulna_l",),
    "left_forearm": ("radius_l", "lunate_l"),
    "left_thigh": ("tibia_l",),
    "left_shank": ("talus_l",),
    "left_foot": ("toes_l",),
    "right_upper_arm": ("ulna_r",),
    "right_forearm": ("radius_r", "lunate_r"),
    "right_thigh": ("tibia_r",),
    "right_shank": ("talus_r",),
    "right_foot": ("toes_r",),
}


EXAMPLE_MESH_SCALE_LINKS: dict[str, tuple[str, ...]] = {
    "head": ("head",),
    "left_upper_arm": ("humerus_l",),
    "left_forearm": ("ulna_l", "radius_l"),
    "left_foot": ("talus_l", "calcn_l", "toes_l"),
    "left_shank": ("tibia_l",),
    "left_thigh": ("femur_l",),
    "right_upper_arm": ("humerus_r",),
    "right_forearm": ("ulna_r", "radius_r"),
    "right_foot": ("talus_r", "calcn_r", "toes_r"),
    "right_shank": ("tibia_r",),
    "right_thigh": ("femur_r",),
}


def scale_project_to_example_skin(
    project: Any,
    skin_joints: dict[str, tuple[float, float, float]],
    translation_map: Any | None,
) -> tuple[Any, dict[str, float]]:
    if translation_map is None:
        return project, {}

    world_transforms = compute_project_link_world_transforms(
        project,
        coordinate_values=getattr(project.simulation, "initial_coordinate_values", {}),
    )
    source_measurements = measure_example_source_segments(world_transforms)
    target_measurements = measure_example_skin_segments(
        {"joints": skin_joints},
        translation_map,
    )
    fit_result = fit_project_system_to_measurements(
        project,
        source_measurements,
        target_measurements,
        build_example_scale_link_map(),
    )
    body_scale_factors = link_scale_factors_from_segment_scale_factors(
        fit_result.segment_scale_factors,
        build_example_visual_scale_link_map(),
    )
    scaled_project = fit_result.project
    scaled_project.translation_maps = list(getattr(project, "translation_maps", []))
    scaled_project.skin_attachments = list(getattr(project, "skin_attachments", []))
    return scaled_project, body_scale_factors


def build_example_scale_report(
    *,
    resolve_resource_path: Callable[[str, str], Path],
    load_example_skin_reference_bundle: Callable[[Path], dict[str, Any] | None],
    build_translation_map: Callable[[], Any],
) -> list[str]:
    project = import_mjcf(
        resolve_resource_path(
            "myofullbody/body/myofullbody.xml",
            "resources/third_party/myofullbody/body/myofullbody.xml",
        )
    ).project
    translation_map = build_translation_map()
    skin_bundle = load_example_skin_reference_bundle(
        resolve_resource_path("skin/SOMA_neutral.npz", "resources/third_party/skin/SOMA_neutral.npz")
    )
    if skin_bundle is None:
        raise RuntimeError("Could not load the reference skin bundle for scale analysis.")

    world_transforms = compute_project_link_world_transforms(
        project,
        coordinate_values=project.simulation.initial_coordinate_values,
    )
    scale_factors = compute_example_segment_scale_factors(
        skin_bundle["joints"],
        world_transforms,
        translation_map,
    )
    if not scale_factors:
        return ["No mapped segment scale factors were computed."]

    sorted_items = sorted(scale_factors.items())
    values = sorted(scale_factors.values())
    median = values[len(values) // 2]
    lines = [f"Example scale median: {median:.4f} ({len(sorted_items)} segments)"]
    for segment_id, factor in sorted_items:
        lines.append(f"{segment_id}: {factor:.4f}")
    return lines


def compute_example_segment_scale_factors(
    skin_joints: dict[str, tuple[float, float, float]],
    world_transforms: dict[str, Any],
    translation_map: Any | None,
) -> dict[str, float]:
    if translation_map is None:
        return {}

    rules_by_segment = {
        getattr(rule, "segment_id", ""): rule
        for rule in translation_map.rules
        if getattr(rule, "segment_id", None)
    }
    scales: dict[str, float] = {}
    for segment_id, rule in rules_by_segment.items():
        source_length = _rule_source_segment_length(rule, skin_joints)
        target_length = example_source_segment_length(segment_id, world_transforms)
        if source_length is None or target_length is None:
            continue
        if source_length <= 1e-8 or target_length <= 1e-8:
            continue
        scales[segment_id] = target_length / source_length
    return scales


def compute_example_skin_alignment(
    project: Any,
    world_transforms: dict[str, Any],
    skin_template: Any,
    translation_map: Any | None,
) -> SimilarityTransform:
    _ = getattr(project, "skin_attachments", None)
    return compute_skin_reference_alignment(world_transforms, skin_template, translation_map)


def refine_target_joints_from_source_visuals(
    project: Any,
    world_transforms: dict[str, Any],
    target_joint_positions: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    return refine_target_joints_from_source_visuals_from_source(
        project,
        world_transforms,
        target_joint_positions,
    )


def compute_skin_joint_alignment(
    skin_joints: dict[str, tuple[float, float, float]],
    world_transforms: dict[str, Any],
    translation_map: Any | None,
) -> SimilarityTransform:
    return compute_joint_alignment_similarity(
        skin_joints,
        world_transforms,
        translation_map,
    )


def compute_skin_reference_alignment(
    world_transforms: dict[str, Any],
    skin_template: Any,
    translation_map: Any | None,
) -> SimilarityTransform:
    template_world = template_world_points(skin_template)
    return compute_reference_alignment_similarity(
        template_world,
        world_transforms,
        translation_map,
    )


def body_frame_landmarks(
    template_world: dict[str, tuple[float, float, float]],
    world_transforms: dict[str, Any],
    translation_map: Any | None,
) -> tuple[dict[str, tuple[float, float, float]], dict[str, tuple[float, float, float]]]:
    if translation_map is None:
        return {}, {}

    landmark_segments = {
        "pelvis": "pelvis",
        "head": "head",
        "left_thigh": "left_thigh",
        "right_thigh": "right_thigh",
    }
    rules_by_target = {
        rule.target_link_id: rule
        for rule in translation_map.rules
    }
    source_points: dict[str, tuple[float, float, float]] = {}
    target_points: dict[str, tuple[float, float, float]] = {}
    for landmark_name, target_link_id in landmark_segments.items():
        rule = rules_by_target.get(target_link_id)
        if rule is None:
            continue
        source_point = template_world.get(target_link_id)
        target_transform = world_transforms.get(rule.source_link_id)
        if source_point is None or target_transform is None:
            continue
        source_points[landmark_name] = source_point
        target_points[landmark_name] = target_transform.translation
    return source_points, target_points


def align_generic_humanoid(vertices: list[list[float]], similarity: SimilarityTransform) -> list[list[float]]:
    aligned: list[list[float]] = []
    for vertex in vertices:
        canonical = obj_vertex_to_template_space(vertex)
        mapped = apply_similarity(canonical, similarity)
        aligned.append([mapped[0], mapped[1], mapped[2]])
    return aligned


def obj_vertex_to_template_space(
    vertex: list[float] | tuple[float, float, float],
) -> tuple[float, float, float]:
    x, y, z = float(vertex[0]), float(vertex[1]), float(vertex[2])
    return (x, z, y)


def reference_body_tail_dirs(translation_map: Any | None) -> dict[str, tuple[float, float, float]]:
    if translation_map is None:
        return {}
    return {
        rule.source_link_id: rule.template_ref_dir
        for rule in translation_map.rules
    }


def template_world_points(project: Any) -> dict[str, tuple[float, float, float]]:
    anatomical_system = project.get_anatomical_system() if hasattr(project, "get_anatomical_system") else None
    link_ids = {link.id for link in (anatomical_system.links if anatomical_system is not None else [])}
    world_transforms = compute_project_link_world_transforms(project)
    return {
        body_id: transform.translation
        for body_id, transform in world_transforms.items()
        if body_id in link_ids
    }


def target_alignment_points(
    world_transforms: dict[str, Any],
    translation_map: Any | None,
) -> dict[str, tuple[float, float, float]]:
    if translation_map is None:
        mapping = {
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
        return {
            source_id: world_transforms[target_id].translation
            for source_id, target_id in mapping.items()
            if target_id in world_transforms
        }
    return {
        rule.target_link_id: world_transforms[rule.source_link_id].translation
        for rule in translation_map.rules
        if rule.source_link_id in world_transforms
        and (rule.target_joint_ids or rule.anchor_target_joint_id is not None)
    }


def _point_landmarks(
    source_points: dict[str, tuple[float, float, float]],
    target_points: dict[str, tuple[float, float, float]],
) -> tuple[dict[str, tuple[float, float, float]], dict[str, tuple[float, float, float]]]:
    landmark_segments = {
        "pelvis": "pelvis",
        "head": "head",
        "left_thigh": "left_thigh",
        "right_thigh": "right_thigh",
    }
    source_landmarks: dict[str, tuple[float, float, float]] = {}
    target_landmarks: dict[str, tuple[float, float, float]] = {}
    for landmark_name, segment_id in landmark_segments.items():
        source_point = source_points.get(segment_id)
        target_point = target_points.get(segment_id)
        if source_point is None or target_point is None:
            continue
        source_landmarks[landmark_name] = source_point
        target_landmarks[landmark_name] = target_point
    return source_landmarks, target_landmarks


def _skin_alignment_points(
    skin_joints: dict[str, tuple[float, float, float]],
    translation_map: Any | None,
) -> dict[str, tuple[float, float, float]]:
    if translation_map is None:
        default_map = {
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
        return {
            link_id: skin_joints[joint_name]
            for link_id, joint_name in default_map.items()
            if joint_name in skin_joints
        }

    return {
        rule.target_link_id: skin_joints[joint_name]
        for rule in translation_map.rules
        if (joint_name := rule_body_anchor_joint(rule)) is not None and joint_name in skin_joints
    }


def solve_axis_aligned_similarity(
    source_points: dict[str, tuple[float, float, float]],
    target_points: dict[str, tuple[float, float, float]],
) -> SimilarityTransform:
    common = [key for key in source_points if key in target_points]
    if not common:
        return SimilarityTransform(
            rotation=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            scale=1.0,
            translation=(0.0, 0.0, 0.0),
        )

    source = [source_points[key] for key in common]
    target = [target_points[key] for key in common]
    source_centroid = (
        sum(point[0] for point in source) / len(source),
        sum(point[1] for point in source) / len(source),
        sum(point[2] for point in source) / len(source),
    )
    target_centroid = (
        sum(point[0] for point in target) / len(target),
        sum(point[1] for point in target) / len(target),
        sum(point[2] for point in target) / len(target),
    )
    centered_source = [
        (point[0] - source_centroid[0], point[1] - source_centroid[1], point[2] - source_centroid[2])
        for point in source
    ]
    centered_target = [
        (point[0] - target_centroid[0], point[1] - target_centroid[1], point[2] - target_centroid[2])
        for point in target
    ]
    rotation = solve_rotation_kabsch(centered_source, centered_target)
    rotated_source = [apply_rotation(point, rotation) for point in centered_source]
    source_energy = sum(dot(point, point) for point in centered_source)
    if source_energy > 1e-8:
        raw_scale = sum(dot(rotated_source[i], centered_target[i]) for i in range(len(centered_source))) / source_energy
        scale = raw_scale if raw_scale > 1e-8 else 1.0
    else:
        scale = 1.0
    translation = (
        target_centroid[0] - (scale * apply_rotation(source_centroid, rotation)[0]),
        target_centroid[1] - (scale * apply_rotation(source_centroid, rotation)[1]),
        target_centroid[2] - (scale * apply_rotation(source_centroid, rotation)[2]),
    )
    return SimilarityTransform(rotation=rotation, scale=scale, translation=translation)


def solve_body_frame_similarity(
    source_points: dict[str, tuple[float, float, float]],
    target_points: dict[str, tuple[float, float, float]],
) -> SimilarityTransform | None:
    required = ("pelvis", "head", "left_thigh", "right_thigh")
    if any(key not in source_points or key not in target_points for key in required):
        return None

    rotation = solve_body_frame_rotation(source_points, target_points)
    common = [key for key in source_points if key in target_points]
    if not common:
        return None

    source = [source_points[key] for key in common]
    target = [target_points[key] for key in common]
    source_centroid = (
        sum(point[0] for point in source) / len(source),
        sum(point[1] for point in source) / len(source),
        sum(point[2] for point in source) / len(source),
    )
    target_centroid = (
        sum(point[0] for point in target) / len(target),
        sum(point[1] for point in target) / len(target),
        sum(point[2] for point in target) / len(target),
    )
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
    return SimilarityTransform(rotation=rotation, scale=scale, translation=translation)


def solve_body_frame_rotation(
    source_points: dict[str, tuple[float, float, float]],
    target_points: dict[str, tuple[float, float, float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    source_basis = frame_basis(source_points)
    target_basis = frame_basis(target_points)
    return matmul(target_basis, transpose(source_basis))


def frame_basis(
    points: dict[str, tuple[float, float, float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    longitudinal = normalize(sub(points["head"], points["pelvis"]))
    lateral = normalize(sub(points["left_thigh"], points["right_thigh"]))
    forward = normalize(cross(lateral, longitudinal))
    if length(forward) < 1e-8:
        return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    lateral = normalize(cross(longitudinal, forward))
    return matrix_from_columns(lateral, forward, longitudinal)


def apply_similarity(point: tuple[float, float, float], similarity: SimilarityTransform) -> tuple[float, float, float]:
    rotated = apply_rotation(point, similarity.rotation)
    return (
        rotated[0] * similarity.scale + similarity.translation[0],
        rotated[1] * similarity.scale + similarity.translation[1],
        rotated[2] * similarity.scale + similarity.translation[2],
    )


def solve_rotation_kabsch(
    source_points: list[tuple[float, float, float]],
    target_points: list[tuple[float, float, float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    if len(source_points) < 3 or len(target_points) < 3:
        return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

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
    matrix: tuple[tuple[float, float, float, float], tuple[float, float, float, float], tuple[float, float, float, float], tuple[float, float, float, float]],
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


def quat_to_matrix(quaternion: tuple[float, float, float, float]) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    w, x, y, z = quaternion
    return (
        (1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)),
        (2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)),
        (2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)),
    )


def apply_rotation(
    point: tuple[float, float, float],
    rotation: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
) -> tuple[float, float, float]:
    return (
        rotation[0][0] * point[0] + rotation[0][1] * point[1] + rotation[0][2] * point[2],
        rotation[1][0] * point[0] + rotation[1][1] * point[1] + rotation[1][2] * point[2],
        rotation[2][0] * point[0] + rotation[2][1] * point[1] + rotation[2][2] * point[2],
    )


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length(v: tuple[float, float, float]) -> float:
    return math.sqrt(dot(v, v))


def normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    magnitude = length(v)
    if magnitude < 1e-8:
        return (0.0, 0.0, 0.0)
    return (v[0] / magnitude, v[1] / magnitude, v[2] / magnitude)


def scale_vec(v: tuple[float, float, float], scalar: float) -> tuple[float, float, float]:
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
    col0: tuple[float, float, float],
    col1: tuple[float, float, float],
    col2: tuple[float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return (
        (col0[0], col1[0], col2[0]),
        (col0[1], col1[1], col2[1]),
        (col0[2], col1[2], col2[2]),
    )


def bind_vertices_to_bodies(vertices: list[list[float]], bodies: list[Any], world_transforms: dict[str, Any]) -> tuple[list[list[float]], list[list[int]]]:
    indexed_points = [
        (index, body.id, world_transforms.get(body.id, body.transform).translation)
        for index, body in enumerate(bodies)
    ]
    weights: list[list[float]] = []
    indices: list[list[int]] = []
    for vx, vy, vz in vertices:
        best_index = 0
        best_distance = math.inf
        for index, _body_id, point in indexed_points:
            dx = vx - point[0]
            dy = vy - point[1]
            dz = vz - point[2]
            distance = dx * dx + dy * dy + dz * dz
            if distance < best_distance:
                best_distance = distance
                best_index = index
        weights.append([1.0])
        indices.append([best_index])
    return weights, indices


def _head_visual_world_centroid(
    project: Any,
    world_transforms: dict[str, Any],
) -> tuple[float, float, float] | None:
    return _link_visual_world_centroid(
        project,
        world_transforms,
        link_id="head",
        preferred_asset_terms=("skull",),
    )


def _link_visual_world_centroid(
    project: Any,
    world_transforms: dict[str, Any],
    *,
    link_id: str,
    preferred_asset_terms: tuple[str, ...] = (),
) -> tuple[float, float, float] | None:
    candidate_assets, link_transform = _link_visual_assets_and_transform(
        project,
        world_transforms,
        link_id=link_id,
        preferred_asset_terms=preferred_asset_terms,
    )
    if candidate_assets is None or link_transform is None:
        return None
    for asset in candidate_assets:
        local_centroid = _mesh_asset_local_centroid(asset)
        if local_centroid is None:
            continue
        return _asset_local_point_to_world(local_centroid, asset, link_transform)
    return None


def move_point_relative_to_reference(
    point: tuple[float, float, float],
    reference_point: tuple[float, float, float] | None,
    factor: float,
) -> tuple[float, float, float]:
    if reference_point is None:
        return point
    return add(reference_point, scale_vec(sub(point, reference_point), factor))


def _link_visual_assets_and_transform(
    project: Any,
    world_transforms: dict[str, Any],
    *,
    link_id: str,
    preferred_asset_terms: tuple[str, ...] = (),
) -> tuple[list[Any] | None, Any | None]:
    anatomical_system = project.get_anatomical_system() if hasattr(project, "get_anatomical_system") else None
    if anatomical_system is None:
        return None, None
    link = next((item for item in anatomical_system.links if item.id == link_id), None)
    if link is None:
        return None, None
    link_transform = world_transforms.get(link_id)
    if link_transform is None:
        return None, None
    asset_map = {asset.id: asset for asset in getattr(project.assets, "items", [])}
    candidate_assets = [asset_map[asset_id] for asset_id in link.asset_ids if asset_id in asset_map]
    if not candidate_assets:
        return None, None
    candidate_assets.sort(
        key=lambda asset: (
            not any(term in asset.id.lower() for term in preferred_asset_terms),
            asset.id,
        )
    )
    return candidate_assets, link_transform


def _asset_local_point_to_world(
    local_point: tuple[float, float, float],
    asset: Any,
    link_transform: Any,
) -> tuple[float, float, float]:
    geom_transform = _asset_geom_transform(asset)
    geom_scaled = apply_scale(local_point, geom_transform["mesh_scale"])
    geom_scaled = apply_scale(geom_scaled, geom_transform["scale"])
    geom_rotated = rotate_vector_by_quaternion(geom_transform["rotation"], geom_scaled)
    geom_positioned = add(geom_rotated, geom_transform["translation"])
    world_offset = rotate_vector_by_quaternion(link_transform.rotation, geom_positioned)
    return add(link_transform.translation, world_offset)


def _mesh_asset_local_centroid(asset: Any) -> tuple[float, float, float] | None:
    vertices = _mesh_asset_local_vertices(asset)
    if not vertices:
        return None
    return (
        sum(vertex[0] for vertex in vertices) / len(vertices),
        sum(vertex[1] for vertex in vertices) / len(vertices),
        sum(vertex[2] for vertex in vertices) / len(vertices),
    )


def _mesh_asset_local_vertices(asset: Any) -> list[tuple[float, float, float]]:
    uri = getattr(asset, "uri", "")
    if not uri:
        return []
    path = Path(uri)
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    if not path.exists():
        return []
    suffix = path.suffix.lower()
    if suffix == ".obj":
        return _load_obj_vertices(path)
    if suffix == ".stl":
        return _load_binary_stl_vertices(path)
    return []


def _load_obj_vertices(path: Path) -> list[tuple[float, float, float]]:
    vertices: list[tuple[float, float, float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("v "):
                continue
            _, x, y, z, *_ = line.split()
            vertices.append((float(x), float(y), float(z)))
    return vertices


def _load_binary_stl_vertices(path: Path) -> list[tuple[float, float, float]]:
    import struct

    data = path.read_bytes()
    if len(data) < 84:
        return []
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    offset = 84
    vertices: list[tuple[float, float, float]] = []
    for _ in range(triangle_count):
        if offset + 50 > len(data):
            break
        offset += 12
        for _vertex in range(3):
            x = float(struct.unpack_from("<f", data, offset)[0])
            y = float(struct.unpack_from("<f", data, offset + 4)[0])
            z = float(struct.unpack_from("<f", data, offset + 8)[0])
            vertices.append((x, y, z))
            offset += 12
        offset += 2
    return vertices


def _asset_geom_transform(asset_record: Any) -> dict[str, tuple[float, float, float] | tuple[float, float, float, float]]:
    annotations = getattr(asset_record, "annotations", {}) or {}
    mesh_scale = _parse_scale_string(annotations.get("mjcf_mesh_scale"))
    return {
        "mesh_scale": mesh_scale,
        "translation": _parse_vec3_string(annotations.get("mjcf_geom_pos")),
        "rotation": _parse_quat_string(annotations.get("mjcf_geom_quat")),
        "scale": _parse_scale_string(annotations.get("mjcf_geom_scale")),
    }


def _parse_vec3_string(value: str | None) -> tuple[float, float, float]:
    if not value:
        return (0.0, 0.0, 0.0)
    parts = value.split()
    return (float(parts[0]), float(parts[1]), float(parts[2]))


def _parse_quat_string(value: str | None) -> tuple[float, float, float, float]:
    if not value:
        return (1.0, 0.0, 0.0, 0.0)
    parts = value.split()
    return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))


def _parse_scale_string(value: str | None) -> tuple[float, float, float]:
    if not value:
        return (1.0, 1.0, 1.0)
    parts = [float(part) for part in value.split()]
    if len(parts) == 1:
        return (parts[0], parts[0], parts[0])
    if len(parts) == 2:
        return (parts[0], parts[1], 1.0)
    return (parts[0], parts[1], parts[2])


def example_unit_scale(segment_scale_factors: dict[str, float]) -> float:
    _ = segment_scale_factors
    return 0.01


def example_body_scale_factors(segment_scale_factors: dict[str, float], unit_scale: float) -> dict[str, float]:
    ratio = {
        segment_id: (unit_scale / factor)
        for segment_id, factor in segment_scale_factors.items()
        if unit_scale > 1e-12 and factor > 1e-12
    }
    return {
        link_id: ratio[segment_id]
        for segment_id, link_ids in EXAMPLE_MESH_SCALE_LINKS.items()
        for link_id in link_ids
        if segment_id in ratio
    }


def example_kinematic_scale_factors(segment_scale_factors: dict[str, float], unit_scale: float) -> dict[str, float]:
    ratio = {
        segment_id: (unit_scale / factor)
        for segment_id, factor in segment_scale_factors.items()
        if unit_scale > 1e-12 and factor > 1e-12
    }
    return {
        link_id: ratio[segment_id]
        for segment_id, link_ids in EXAMPLE_KINEMATIC_SCALE_LINKS.items()
        for link_id in link_ids
        if segment_id in ratio
    }


def apply_scale(vertex: tuple[float, float, float], scale: tuple[float, float, float]) -> tuple[float, float, float]:
    return (vertex[0] * scale[0], vertex[1] * scale[1], vertex[2] * scale[2])


def apply_uniform_scale(vertex: tuple[float, float, float], scale: float) -> tuple[float, float, float]:
    return (vertex[0] * scale, vertex[1] * scale, vertex[2] * scale)


def rule_body_anchor_joint(rule: Any) -> str | None:
    target_joint_ids = list(getattr(rule, "target_joint_ids", ()) or ())
    if target_joint_ids:
        return str(target_joint_ids[0])
    anchor_joint = getattr(rule, "anchor_target_joint_id", None)
    if anchor_joint is None:
        return None
    return str(anchor_joint)


def rule_body_tail_joint(rule: Any) -> str | None:
    target_joint_ids = list(getattr(rule, "target_joint_ids", ()) or ())
    if len(target_joint_ids) >= 2:
        return str(target_joint_ids[-1])
    anchor_joint = getattr(rule, "anchor_target_joint_id", None)
    if anchor_joint is not None:
        return str(anchor_joint)
    if target_joint_ids:
        return str(target_joint_ids[-1])
    return None


def _rule_source_segment_length(
    rule: Any,
    skin_joints: dict[str, tuple[float, float, float]],
) -> float | None:
    target_joint_ids = list(getattr(rule, "target_joint_ids", ()) or ())
    reduction_mode = str(getattr(rule, "reduction_mode", "direct") or "direct")
    if reduction_mode in {"ignore", "inherit_parent"}:
        return None
    if len(target_joint_ids) < 2:
        return None
    if any(joint_name not in skin_joints for joint_name in target_joint_ids):
        return None
    if reduction_mode == "chain_sum":
        return sum(
            length(sub(skin_joints[target_joint_ids[index + 1]], skin_joints[target_joint_ids[index]]))
            for index in range(len(target_joint_ids) - 1)
        )
    return length(sub(skin_joints[target_joint_ids[-1]], skin_joints[target_joint_ids[0]]))


__all__ = [
    "SimilarityTransform",
    "align_generic_humanoid",
    "bind_vertices_to_bodies",
    "build_example_scale_report",
    "compute_example_segment_scale_factors",
    "compute_example_skin_alignment",
    "compute_skin_joint_alignment",
    "compute_skin_reference_alignment",
    "reference_body_tail_dirs",
    "rule_body_anchor_joint",
    "scale_project_to_example_skin",
    "template_world_points",
]

from __future__ import annotations

from pathlib import Path
from typing import Any

from melos.core.retarget.model import SegmentMeasurement, SegmentMeasurementSet


_REPO_ROOT = Path(__file__).resolve().parents[6]


_EXAMPLE_TARGET_JOINT_BODY_MAP: dict[str, str] = {
    "Root": "pelvis",
    "Hips": "pelvis",
    "Spine1": "torso",
    "Chest": "thorax",
    "Neck1": "neck",
    "Head": "head",
    "LeftShoulder": "humphant1_l",
    "LeftArm": "ulna_l",
    "LeftForeArm": "lunate_l",
    "LeftHand": "lunate_l",
    "RightShoulder": "humphant1_r",
    "RightArm": "ulna_r",
    "RightForeArm": "lunate_r",
    "RightHand": "lunate_r",
    "LeftLeg": "femur_l",
    "LeftShin": "tibia_l",
    "LeftFoot": "calcn_l",
    "LeftToeBase": "toes_l",
    "RightLeg": "femur_r",
    "RightShin": "tibia_r",
    "RightFoot": "calcn_r",
    "RightToeBase": "toes_r",
}


_EXAMPLE_TARGET_JOINT_SECONDARY_LINKS: dict[str, tuple[str, tuple[float, float, float]]] = {
    "Chest": ("thorax", (0.0, 1.0, 0.0)),
    "Neck1": ("neck", (1.0, 0.0, 0.0)),
    "Head": ("head", (1.0, 0.0, 0.0)),
    "LeftShoulder": ("clavicle_l", (1.0, 0.0, 0.0)),
    "LeftArm": ("humerus_l", (0.0, 0.0, 1.0)),
    "LeftForeArm": ("ulna_l", (0.0, 0.0, 1.0)),
    "LeftHand": ("radius_l", (0.0, 0.0, 1.0)),
    "RightShoulder": ("clavicle_r", (1.0, 0.0, 0.0)),
    "RightArm": ("humerus_r", (0.0, 0.0, 1.0)),
    "RightForeArm": ("ulna_r", (0.0, 0.0, 1.0)),
    "RightHand": ("radius_r", (0.0, 0.0, 1.0)),
}



_EXAMPLE_SOURCE_SEGMENT_BODY_PAIRS: dict[str, tuple[str, str]] = {
    "head": ("neck", "head"),
    "left_shoulder_girdle": ("thorax", "humphant1_l"),
    "left_upper_arm": ("humerus_l", "ulna_l"),
    "left_forearm": ("ulna_l", "lunate_l"),
    "left_thigh": ("femur_l", "tibia_l"),
    "left_shank": ("tibia_l", "talus_l"),
    "left_foot": ("calcn_l", "toes_l"),
    "right_shoulder_girdle": ("thorax", "humphant1_r"),
    "right_upper_arm": ("humerus_r", "ulna_r"),
    "right_forearm": ("ulna_r", "lunate_r"),
    "right_thigh": ("femur_r", "tibia_r"),
    "right_shank": ("tibia_r", "talus_r"),
    "right_foot": ("calcn_r", "toes_r"),
}

_EXAMPLE_SOURCE_SEGMENT_SCALE_LINKS: dict[str, tuple[str, ...]] = {
    "head": ("head",),
    "left_shoulder_girdle": ("clavicle_l", "clavphant_l", "scapphant_l"),
    "left_upper_arm": ("ulna_l",),
    "left_forearm": ("radius_l", "lunate_l"),
    "left_thigh": ("tibia_l",),
    "left_shank": ("talus_l",),
    "left_foot": ("toes_l",),
    "right_shoulder_girdle": ("clavicle_r", "clavphant_r", "scapphant_r"),
    "right_upper_arm": ("ulna_r",),
    "right_forearm": ("radius_r", "lunate_r"),
    "right_thigh": ("tibia_r",),
    "right_shank": ("talus_r",),
    "right_foot": ("toes_r",),
}

_EXAMPLE_SOURCE_VISUAL_SCALE_LINKS: dict[str, tuple[str, ...]] = {
    "head": ("head",),
    "left_shoulder_girdle": ("clavicle_l", "clavphant_l", "scapula_l", "scapphant_l", "humerus_l"),
    "left_upper_arm": ("humerus_l",),
    "left_forearm": ("ulna_l", "radius_l"),
    "left_foot": ("talus_l", "calcn_l", "toes_l"),
    "left_shank": ("tibia_l",),
    "left_thigh": ("femur_l",),
    "right_shoulder_girdle": ("clavicle_r", "clavphant_r", "scapula_r", "scapphant_r", "humerus_r"),
    "right_upper_arm": ("humerus_r",),
    "right_forearm": ("ulna_r", "radius_r"),
    "right_foot": ("talus_r", "calcn_r", "toes_r"),
    "right_shank": ("tibia_r",),
    "right_thigh": ("femur_r",),
}


def build_example_target_joint_positions(
    world_transforms: dict[str, Any],
) -> dict[str, tuple[float, float, float]]:
    positions = {
        joint_name: world_transforms[body_id].translation
        for joint_name, body_id in _EXAMPLE_TARGET_JOINT_BODY_MAP.items()
        if body_id in world_transforms
    }
    if "Head" in positions and "Neck1" in positions:
        head_dir = _sub(positions["Head"], positions["Neck1"])
        positions["HeadEnd"] = _add(positions["Head"], head_dir)
    if "LeftToeBase" in positions and "LeftFoot" in positions:
        toe_dir = _sub(positions["LeftToeBase"], positions["LeftFoot"])
        positions["LeftToeEnd"] = _add(positions["LeftToeBase"], toe_dir)
    if "RightToeBase" in positions and "RightFoot" in positions:
        toe_dir = _sub(positions["RightToeBase"], positions["RightFoot"])
        positions["RightToeEnd"] = _add(positions["RightToeBase"], toe_dir)
    return positions


def refine_target_joints_from_source_visuals(
    project: Any,
    world_transforms: dict[str, Any],
    target_joint_positions: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    refined = dict(target_joint_positions)
    neck_origin = getattr(world_transforms.get("neck"), "translation", None)
    chest_visual_point = _link_visual_world_centroid(
        project,
        world_transforms,
        link_id="torso",
        preferred_asset_terms=("ribcage", "thorax"),
    )
    if chest_visual_point is not None:
        refined["Chest"] = (
            move_point_relative_to_reference(chest_visual_point, neck_origin, 0.6)
            if neck_origin is not None
            else chest_visual_point
        )
    head_visual_point = _head_visual_world_centroid(project, world_transforms)
    if head_visual_point is not None:
        adjusted_head = (
            move_point_relative_to_reference(head_visual_point, neck_origin, 1.6)
            if neck_origin is not None
            else head_visual_point
        )
        previous_head = refined.get("Head")
        refined["Head"] = adjusted_head
        if previous_head is not None and "HeadEnd" in refined:
            delta = _sub(refined["HeadEnd"], previous_head)
            refined["HeadEnd"] = _add(adjusted_head, delta)

    for shoulder_name, clavicle_link_id in (
        ("LeftShoulder", "clavicle_l"),
        ("RightShoulder", "clavicle_r"),
    ):
        raw_shoulder = refined.get(shoulder_name)
        clavicle_visual_point = _link_visual_world_centroid(
            project,
            world_transforms,
            link_id=clavicle_link_id,
        )
        if clavicle_visual_point is None:
            clavicle_visual_point = getattr(world_transforms.get(clavicle_link_id), "translation", None)
        if raw_shoulder is None or clavicle_visual_point is None:
            continue
        refined[shoulder_name] = _scale_vec(_add(raw_shoulder, clavicle_visual_point), 0.5)
    return refined



def build_example_target_joint_secondary_directions(
    world_transforms: dict[str, Any],
) -> dict[str, tuple[float, float, float]]:
    directions: dict[str, tuple[float, float, float]] = {}
    for joint_name, (link_id, local_axis) in _EXAMPLE_TARGET_JOINT_SECONDARY_LINKS.items():
        transform = world_transforms.get(link_id)
        if transform is None:
            continue
        direction = _quat_rotate(transform.rotation, local_axis)
        if _length(direction) <= 1e-8:
            continue
        directions[joint_name] = _normalize(direction)
    return directions




def build_example_scale_link_map() -> dict[str, tuple[str, ...]]:
    return {segment_id: tuple(link_ids) for segment_id, link_ids in _EXAMPLE_SOURCE_SEGMENT_SCALE_LINKS.items()}


def build_example_visual_scale_link_map() -> dict[str, tuple[str, ...]]:
    return {segment_id: tuple(link_ids) for segment_id, link_ids in _EXAMPLE_SOURCE_VISUAL_SCALE_LINKS.items()}


def example_source_segment_length(
    segment_id: str,
    world_transforms: dict[str, Any],
) -> float | None:
    body_pair = _EXAMPLE_SOURCE_SEGMENT_BODY_PAIRS.get(segment_id)
    if body_pair is None:
        return None
    proximal = world_transforms.get(body_pair[0])
    distal = world_transforms.get(body_pair[1])
    if proximal is None or distal is None:
        return None
    return _length(_sub(distal.translation, proximal.translation))


def measure_example_source_segments(
    world_transforms: dict[str, Any],
) -> SegmentMeasurementSet:
    items = [
        SegmentMeasurement(segment_id=segment_id, length=length)
        for segment_id in sorted(_EXAMPLE_SOURCE_SEGMENT_BODY_PAIRS)
        if (length := example_source_segment_length(segment_id, world_transforms)) is not None
    ]
    return SegmentMeasurementSet(
        items=items,
        units="m",
    )


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
    return _add(reference_point, _scale_vec(_sub(point, reference_point), factor))



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
    geom_scaled = _apply_scale(local_point, geom_transform["mesh_scale"])
    geom_scaled = _apply_scale(geom_scaled, geom_transform["scale"])
    geom_rotated = _quat_rotate(geom_transform["rotation"], geom_scaled)
    geom_positioned = _add(geom_rotated, geom_transform["translation"])
    world_offset = _quat_rotate(link_transform.rotation, geom_positioned)
    return _add(link_transform.translation, world_offset)



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



def _apply_scale(vertex: tuple[float, float, float], scale: tuple[float, float, float]) -> tuple[float, float, float]:
    return (vertex[0] * scale[0], vertex[1] * scale[1], vertex[2] * scale[2])



def _quat_rotate(
    q: tuple[float, float, float, float],
    v: tuple[float, float, float],
) -> tuple[float, float, float]:
    rotated = _quat_multiply(_quat_multiply(q, (0.0, v[0], v[1], v[2])), _quat_conjugate(q))
    return (rotated[1], rotated[2], rotated[3])



def _quat_multiply(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )



def _quat_conjugate(q: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    return (q[0], -q[1], -q[2], -q[3])



def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])



def _scale_vec(v: tuple[float, float, float], scalar: float) -> tuple[float, float, float]:
    return (v[0] * scalar, v[1] * scalar, v[2] * scalar)



def _length(v: tuple[float, float, float]) -> float:
    return (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) ** 0.5



def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    length = _length(v)
    if length <= 1e-8:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)



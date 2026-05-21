"""Project-level Blender operators for melos authoring."""

from __future__ import annotations

import importlib
import math
from pathlib import Path
from typing import Any, Callable, TypedDict, cast

from melos.core.common.transforms import (
    multiply_quaternions,
    normalize_quaternion_or_identity,
)
from melos.core.common.types import Transform
from melos.core.validation import validate_project

from melos.blender.bpy_io.project import build_project_from_scene, save_project_from_scene
from melos.blender.bpy_io.skin_bundle import (
    SKIN_REFERENCE_KIND_BODY_MESH,
    SKIN_REFERENCE_KIND_PROP,
)
from melos.blender.constants import SCENE_SETTINGS_ATTRIBUTE
from melos.blender.services.validation import format_validation_report


try:
    bpy = importlib.import_module("bpy")
except ModuleNotFoundError:
    bpy = None


if bpy is not None:
    OperatorBase = bpy.types.Operator
else:
    class OperatorBase:
        pass


_PACKAGE_ROOT = Path(__file__).resolve().parents[3]
_PACKAGED_RESOURCES = _PACKAGE_ROOT / "resources"
_REPO_ROOT = Path(__file__).resolve().parents[7]


class _GeomTransform(TypedDict):
    mesh_scale: tuple[float, float, float]
    translation: tuple[float, float, float]
    rotation: tuple[float, float, float, float]
    scale: tuple[float, float, float]


class _SimilarityTransform(TypedDict):
    rotation: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
    scale: float
    translation: tuple[float, float, float]


class MELOS_OT_validate_project(OperatorBase):
    """Validate the current Blender-authored melos project."""

    bl_idname = "melos.validate_project"
    bl_label = "Validate melos Project"

    def execute(self, context):
        try:
            project = build_project_from_scene(context.scene)
            report = validate_project(project)
            for message in format_validation_report(report):
                _report(self, {"INFO" if not report.has_errors else "WARNING"}, message)
            return {"FINISHED"}
        except Exception as exc:  # pragma: no cover - Blender-facing path
            _report(self, {"ERROR"}, str(exc))
            return {"CANCELLED"}


class MELOS_OT_export_project_json(OperatorBase):
    """Build and export the current Blender-authored melos project as JSON."""

    bl_idname = "melos.export_project_json"
    bl_label = "Export melos Project"

    def execute(self, context):
        try:
            settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
            path = Path(settings.export_path)
            save_project_from_scene(context.scene, path)
            _report(self, {"INFO"}, f"Saved melos project to {path}.")
            return {"FINISHED"}
        except Exception as exc:  # pragma: no cover - Blender-facing path
            _report(self, {"ERROR"}, str(exc))
            return {"CANCELLED"}


class MELOS_OT_create_example_project(OperatorBase):
    bl_idname = "melos.create_example_project"
    bl_label = "Create Example Project"

    def execute(self, context):
        try:
            _run_create_example_project(context, include_skin=True)
            _report(self, {"INFO"}, "Example project created.")
            return {"FINISHED"}
        except Exception as exc:  # pragma: no cover - Blender-facing path
            _report(self, {"ERROR"}, str(exc))
            return {"CANCELLED"}


class MELOS_OT_create_example_model_project(OperatorBase):
    bl_idname = "melos.create_example_model_project"
    bl_label = "Import MuJoCo Model Only"

    def execute(self, context):
        try:
            _run_create_example_project(context, include_skin=False)
            _report(self, {"INFO"}, "Example project (model only) created.")
            return {"FINISHED"}
        except Exception as exc:  # pragma: no cover - Blender-facing path
            _report(self, {"ERROR"}, str(exc))
            return {"CANCELLED"}


class MELOS_OT_analyze_example_scale(OperatorBase):
    bl_idname = "melos.analyze_example_scale"
    bl_label = "Analyze Example Scale"

    def execute(self, context):
        try:
            report_lines = _build_example_scale_report()
            for line in report_lines:
                _report(self, {"INFO"}, line)
            return {"FINISHED"}
        except Exception as exc:  # pragma: no cover - Blender-facing path
            _report(self, {"ERROR"}, str(exc))
            return {"CANCELLED"}


class MELOS_OT_toggle_example_body_mesh_references(OperatorBase):
    bl_idname = "melos.toggle_example_body_mesh_references"
    bl_label = "Toggle MuJoCo Body Mesh References"

    def execute(self, context):
        try:
            body_mesh_objects = _example_body_mesh_reference_objects(context.scene)
            if not body_mesh_objects:
                _report(self, {"WARNING"}, "No MuJoCo body mesh reference objects found in this scene.")
                return {"CANCELLED"}
            make_visible = not _example_body_mesh_references_visible(context.scene)
            count = _set_example_body_mesh_reference_visibility(
                context.scene,
                visible=make_visible,
            )
            action = "Shown" if make_visible else "Hidden"
            _report(self, {"INFO"}, f"{action} {count} MuJoCo body mesh reference objects.")
            return {"FINISHED"}
        except Exception as exc:  # pragma: no cover - Blender-facing path
            _report(self, {"ERROR"}, str(exc))
            return {"CANCELLED"}


def _run_create_example_project(
    context: Any,
    *,
    create_object: Callable[[str, Any], Any] | None = None,
    create_armature_object: Callable[[str, Any, Any], Any] | None = None,
    create_mesh_object: Callable[[str, Any, Any], Any] | None = None,
    include_skin: bool = True,
) -> Any:
    from melos.blender.services.example_workflow import run_create_example_project

    return run_create_example_project(
        context,
        create_object=create_object,
        create_armature_object=create_armature_object,
        create_mesh_object=create_mesh_object,
        include_skin=include_skin,
    )


def _create_muscle_display_objects(
    project: Any,
    context: Any,
    arm_obj: Any,
    world_transforms: dict[str, Any],
    *,
    create_mesh_object: Callable[[str, Any, Any], Any] | None = None,
) -> list[Any]:
    from melos.blender.bpy_io.skinned_import import build_weighted_mesh_object, rotate_vector_by_quaternion
    from melos.core.system.enums import ActuatorKind

    anatomical_system = project.get_anatomical_system() if hasattr(project, "get_anatomical_system") else None
    if anatomical_system is None:
        return []

    link_index_map = {link.id: index for index, link in enumerate(anatomical_system.links)}
    link_name_map = {index: link.id for index, link in enumerate(anatomical_system.links)}
    site_map = {site.id: site for site in anatomical_system.sites}
    created: list[Any] = []

    for actuator in anatomical_system.actuators:
        if actuator.kind != ActuatorKind.MUSCLE:
            continue
        vertices: list[list[float]] = []
        edges: list[list[int]] = []
        bone_weights: list[list[float]] = []
        bone_indices: list[list[int]] = []
        for point_index, site_id in enumerate(actuator.site_ids):
            site = site_map.get(site_id)
            if site is None:
                continue
            link_id = site.link_id or anatomical_system.root_link_id or (anatomical_system.links[0].id if anatomical_system.links else "")
            link_transform = world_transforms.get(link_id)
            if link_transform is None:
                continue
            point_position = (
                float(site.transform.translation[0]),
                float(site.transform.translation[1]),
                float(site.transform.translation[2]),
            )
            offset = rotate_vector_by_quaternion(link_transform.rotation, point_position)
            world_point = (
                link_transform.translation[0] + offset[0],
                link_transform.translation[1] + offset[1],
                link_transform.translation[2] + offset[2],
            )
            vertices.append([float(world_point[0]), float(world_point[1]), float(world_point[2])])
            bone_weights.append([1.0])
            bone_indices.append([link_index_map.get(link_id, 0)])
            if point_index > 0:
                edges.append([point_index - 1, point_index])
        if len(vertices) < 2:
            continue
        muscle_obj = build_weighted_mesh_object(
            project,
            vertices,
            [],
            bone_weights,
            bone_indices,
            link_name_map,
            context,
            arm_obj=arm_obj,
            create_mesh_object=create_mesh_object,
            mesh_name=f"muscle_{actuator.id}",
            edges=edges,
            target_system=anatomical_system,
        )
        if hasattr(muscle_obj, "display_type"):
            muscle_obj.display_type = "WIRE"
        if hasattr(muscle_obj, "show_in_front"):
            muscle_obj.show_in_front = True
        if hasattr(muscle_obj, "hide_viewport"):
            muscle_obj.hide_viewport = False
        created.append(muscle_obj)
    return created


def _create_body_mesh_objects(
    project: Any,
    context: Any,
    arm_obj: Any,
    world_transforms: dict[str, Any],
    body_objects: dict[str, Any],
    *,
    body_scale_factors: dict[str, float] | None = None,
    create_mesh_object: Callable[[str, Any, Any], Any] | None = None,
    attach_to_armature: bool = True,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_dirs: dict[str, tuple[float, float, float]] | None = None,
    display_scale_factor: float = 1.0,
) -> list[Any]:
    from melos.blender.bpy_io.skinned_import import (
        _build_child_map,
        _build_parent_map,
        _default_bone_tail,
        build_mesh_object,
        build_weighted_mesh_object,
        rotate_vector_by_quaternion,
    )

    anatomical_system = project.get_anatomical_system() if hasattr(project, "get_anatomical_system") else None
    if anatomical_system is None:
        return []

    asset_map = {asset.id: asset for asset in project.assets.items}
    body_index_map = {body.id: index for index, body in enumerate(anatomical_system.links)}
    body_name_map = {index: body.id for index, body in enumerate(anatomical_system.links)}
    child_map = _build_child_map(anatomical_system)
    parent_map = _build_parent_map(anatomical_system)
    created: list[Any] = []
    effective_body_scale_factors = body_scale_factors or {}

    for body in anatomical_system.links:
        source_transform = world_transforms.get(body.id)
        if source_transform is None:
            continue
        display_transform = _example_body_mesh_display_transform(
            body.id,
            source_transform=source_transform,
            world_transforms=world_transforms,
            child_map=child_map,
            parent_map=parent_map,
            reference_body_anchors=reference_body_anchors,
            reference_body_tail_points=reference_body_tail_points,
            reference_body_tail_dirs=reference_body_tail_dirs,
            default_bone_tail=_default_bone_tail,
        )
        body_scale = effective_body_scale_factors.get(body.id, 1.0) * float(display_scale_factor)
        for asset_id in body.asset_ids:
            asset_record = asset_map.get(asset_id)
            if asset_record is None:
                continue
            asset_path = Path(asset_record.uri)
            if not asset_path.exists():
                continue
            vertices, faces = _load_binary_stl_mesh(asset_path)
            geom_transform = _asset_geom_transform(asset_record)
            transformed_vertices = []
            scaled_geom_translation = _apply_uniform_scale(geom_transform['translation'], body_scale)
            for vertex in vertices:
                vertex_tuple = (float(vertex[0]), float(vertex[1]), float(vertex[2]))
                mesh_scaled_vertex = _apply_scale(vertex_tuple, geom_transform['mesh_scale'])
                scaled_vertex = _apply_scale(mesh_scaled_vertex, geom_transform['scale'])
                scaled_vertex = _apply_uniform_scale(scaled_vertex, body_scale)
                geom_rotated = rotate_vector_by_quaternion(geom_transform['rotation'], scaled_vertex)
                geom_positioned = (
                    geom_rotated[0] + scaled_geom_translation[0],
                    geom_rotated[1] + scaled_geom_translation[1],
                    geom_rotated[2] + scaled_geom_translation[2],
                )
                rotated = rotate_vector_by_quaternion(display_transform.rotation, geom_positioned)
                transformed_vertices.append([
                    display_transform.translation[0] + rotated[0],
                    display_transform.translation[1] + rotated[1],
                    display_transform.translation[2] + rotated[2],
                ])
            if attach_to_armature:
                bone_index = body_index_map.get(body.id, 0)
                bone_weights = [[1.0] for _ in transformed_vertices]
                bone_indices = [[bone_index] for _ in transformed_vertices]
                mesh_obj = build_weighted_mesh_object(
                    project,
                    transformed_vertices,
                    faces,
                    bone_weights,
                    bone_indices,
                    body_name_map,
                    context,
                    arm_obj=arm_obj,
                    create_mesh_object=create_mesh_object,
                    mesh_name=f"body_{body.id}_{asset_id}",
                    target_system=anatomical_system,
                )
            else:
                mesh_obj = build_mesh_object(
                    project,
                    transformed_vertices,
                    faces,
                    context,
                    create_mesh_object=create_mesh_object,
                    mesh_name=f"body_{body.id}_{asset_id}",
                    target_system=anatomical_system,
                )
            if hasattr(mesh_obj, "display_type"):
                mesh_obj.display_type = "TEXTURED" if attach_to_armature else "WIRE"
            if hasattr(mesh_obj, 'location'):
                mesh_obj.location = (0.0, 0.0, 0.0)
            if hasattr(mesh_obj, 'rotation_mode'):
                mesh_obj.rotation_mode = 'QUATERNION'
            if hasattr(mesh_obj, 'rotation_quaternion'):
                mesh_obj.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            if not attach_to_armature and hasattr(mesh_obj, 'show_in_front'):
                mesh_obj.show_in_front = True
            created.append(mesh_obj)
    return created


def _asset_geom_transform(asset_record: Any) -> _GeomTransform:
    annotations = getattr(asset_record, 'annotations', {}) or {}
    mesh_scale = _parse_scale_string(annotations.get('mjcf_mesh_scale'))
    translation = _parse_vec3_string(annotations.get('mjcf_geom_pos'))
    rotation = _parse_quat_string(annotations.get('mjcf_geom_quat'))
    scale = _parse_scale_string(annotations.get('mjcf_geom_scale'))
    return {
        'mesh_scale': mesh_scale,
        'translation': translation,
        'rotation': rotation,
        'scale': scale,
    }


def _load_obj_mesh(path: Path) -> tuple[list[list[float]], list[list[int]]]:
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    with path.open(encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line.startswith("v "):
                _, xs, ys, zs = line.split()[:4]
                vertices.append([float(xs), float(ys), float(zs)])
            elif line.startswith("f "):
                indices = []
                for token in line.split()[1:4]:
                    indices.append(int(token.split("/")[0]) - 1)
                if len(indices) == 3:
                    faces.append(indices)
    return vertices, faces


def _load_binary_stl_mesh(path: Path) -> tuple[list[list[float]], list[list[int]]]:
    data = path.read_bytes()
    if len(data) < 84:
        return [], []
    triangle_count = int.from_bytes(data[80:84], "little")
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    offset = 84
    for _ in range(triangle_count):
        if offset + 50 > len(data):
            break
        offset += 12
        triangle_indices: list[int] = []
        for _vertex in range(3):
            x = _read_float32(data, offset)
            y = _read_float32(data, offset + 4)
            z = _read_float32(data, offset + 8)
            vertices.append([x, y, z])
            triangle_indices.append(len(vertices) - 1)
            offset += 12
        faces.append(triangle_indices)
        offset += 2
    return vertices, faces


def _scale_project_to_example_skin(
    project: Any,
    skin_joints: dict[str, tuple[float, float, float]],
    translation_map: Any | None,
) -> tuple[Any, dict[str, float]]:
    from melos.blender.services.example_alignment import scale_project_to_example_skin

    return scale_project_to_example_skin(project, skin_joints, translation_map)



def _build_example_scale_report() -> list[str]:
    from melos.blender.services.example_alignment import build_example_scale_report
    from melos.skin.mappings.myofullbody_to_human_v1 import build_myofullbody_translation_map

    return build_example_scale_report(
        resolve_resource_path=_resolve_resource_path,
        load_example_skin_reference_bundle=_load_example_skin_reference_bundle,
        build_translation_map=build_myofullbody_translation_map,
    )


def _compute_example_segment_scale_factors(
    skin_joints: dict[str, tuple[float, float, float]],
    world_transforms: dict[str, Any],
    translation_map: Any | None,
) -> dict[str, float]:
    from melos.blender.services.example_alignment import compute_example_segment_scale_factors

    return compute_example_segment_scale_factors(skin_joints, world_transforms, translation_map)


def _build_example_target_joint_positions(
    world_transforms: dict[str, Any],
) -> dict[str, tuple[float, float, float]]:
    from melos.sim.mujoco.adapters.example_source import build_example_target_joint_positions

    return build_example_target_joint_positions(world_transforms)


def _load_example_skin_reference_bundle(path: Path) -> dict[str, Any] | None:
    from melos.skin.adapters.skin_bundle import load_example_skin_reference_bundle

    return load_example_skin_reference_bundle(path)


def _compute_skin_joint_alignment(
    skin_joints: dict[str, tuple[float, float, float]],
    world_transforms: dict[str, Any],
    translation_map: Any | None,
) -> _SimilarityTransform:
    from melos.blender.services.example_alignment import compute_skin_joint_alignment

    return compute_skin_joint_alignment(skin_joints, world_transforms, translation_map)

def _rule_body_anchor_joint(rule: Any) -> str | None:
    from melos.blender.services.example_alignment import rule_body_anchor_joint

    return rule_body_anchor_joint(rule)


def _rule_body_tail_joint(rule: Any) -> str | None:
    from melos.blender.services.example_alignment import rule_body_tail_joint

    return rule_body_tail_joint(rule)


def _collapse_joint_weights_to_bodies(
    skin_bundle: dict[str, Any],
    bodies: list[Any],
    translation_map: Any | None,
) -> tuple[list[list[float]], list[list[int]]]:
    joint_to_body = _build_target_joint_to_body_map(skin_bundle["joint_names"], translation_map)
    body_index_by_id = {body.id: index for index, body in enumerate(bodies)}
    vertex_count = len(skin_bundle["vertices"])
    vertex_body_weights: list[dict[int, float]] = [dict() for _ in range(vertex_count)]

    weight_data = skin_bundle["weight_data"]
    weight_indices = skin_bundle["weight_indices"]
    weight_indptr = skin_bundle["weight_indptr"]
    joint_names = skin_bundle["joint_names"]

    for joint_index, joint_name in enumerate(joint_names):
        body_id = joint_to_body.get(joint_name)
        body_index = body_index_by_id.get(body_id or "")
        if body_index is None:
            continue
        start = weight_indptr[joint_index]
        end = weight_indptr[joint_index + 1]
        for item_index in range(start, end):
            vertex_index = weight_indices[item_index]
            weight = weight_data[item_index]
            if weight <= 0.0:
                continue
            accum = vertex_body_weights[vertex_index]
            accum[body_index] = accum.get(body_index, 0.0) + weight

    bone_weights: list[list[float]] = []
    bone_indices: list[list[int]] = []
    fallback_index = 0
    for per_vertex in vertex_body_weights:
        if not per_vertex:
            bone_weights.append([1.0])
            bone_indices.append([fallback_index])
            continue
        sorted_items = sorted(per_vertex.items(), key=lambda item: item[1], reverse=True)[:4]
        total = sum(weight for _, weight in sorted_items)
        if total <= 1e-8:
            bone_weights.append([1.0])
            bone_indices.append([fallback_index])
            continue
        bone_indices.append([index for index, _ in sorted_items])
        bone_weights.append([weight / total for _, weight in sorted_items])
    return bone_weights, bone_indices


def _build_target_joint_to_body_map(
    joint_names: list[str],
    translation_map: Any | None,
) -> dict[str, str]:
    joint_to_body: dict[str, str] = {
        "Root": "pelvis",
        "HeadEnd": "head",
        "Jaw": "head",
        "LeftEye": "head",
        "RightEye": "head",
        "LeftHand": "radius_l",
        "RightHand": "radius_r",
        "LeftToeBase": "calcn_l",
        "LeftToeEnd": "calcn_l",
        "RightToeBase": "calcn_r",
        "RightToeEnd": "calcn_r",
    }

    if translation_map is not None:
        for rule in translation_map.rules:
            source_link_id = getattr(rule, "source_link_id", None)
            if not source_link_id:
                continue
            anchor_joint = getattr(rule, "anchor_target_joint_id", None)
            if anchor_joint:
                joint_to_body.setdefault(anchor_joint, source_link_id)
            for joint_name in getattr(rule, "target_joint_ids", ()):
                joint_to_body.setdefault(joint_name, source_link_id)

    for joint_name in joint_names:
        if joint_name.startswith("LeftHand"):
            joint_to_body.setdefault(joint_name, "radius_l")
        elif joint_name.startswith("RightHand"):
            joint_to_body.setdefault(joint_name, "radius_r")

    return joint_to_body


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


def _apply_uniform_scale(vertex: tuple[float, float, float], scale: float) -> tuple[float, float, float]:
    return (vertex[0] * scale, vertex[1] * scale, vertex[2] * scale)


def _example_body_mesh_display_transform(
    body_id: str,
    *,
    source_transform: Transform,
    world_transforms: dict[str, Any],
    child_map: dict[str, list[str]],
    parent_map: dict[str, str],
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_dirs: dict[str, tuple[float, float, float]] | None = None,
    default_bone_tail: Callable[..., tuple[float, float, float]] | None = None,
) -> Transform:
    if (
        not reference_body_anchors
        and not reference_body_tail_points
        and not reference_body_tail_dirs
    ):
        return source_transform

    tail_resolver = default_bone_tail
    if tail_resolver is None:
        from melos.blender.bpy_io.skinned_import import _default_bone_tail as tail_resolver

    source_head = (
        float(source_transform.translation[0]),
        float(source_transform.translation[1]),
        float(source_transform.translation[2]),
    )
    display_head = source_head
    if reference_body_anchors is not None and body_id in reference_body_anchors:
        display_head = tuple(float(value) for value in reference_body_anchors[body_id])

    source_tail = tail_resolver(body_id, world_transforms, child_map, parent_map)
    display_tail = tail_resolver(
        body_id,
        world_transforms,
        child_map,
        parent_map,
        reference_body_anchors=reference_body_anchors,
        reference_body_tail_points=reference_body_tail_points,
        reference_body_tail_dirs=reference_body_tail_dirs,
    )

    rotation = tuple(float(value) for value in source_transform.rotation)
    source_direction = _vec_sub(source_tail, source_head)
    display_direction = _vec_sub(display_tail, display_head)
    if _vec_length(source_direction) > 1e-8 and _vec_length(display_direction) > 1e-8:
        align_rotation = _quat_between_vectors(source_direction, display_direction)
        rotation = normalize_quaternion_or_identity(
            multiply_quaternions(align_rotation, rotation)
        )

    return Transform(translation=display_head, rotation=rotation)


def _quat_between_vectors(
    source: tuple[float, float, float],
    target: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    source_dir = _vec_normalize(source)
    target_dir = _vec_normalize(target)
    if _vec_length(source_dir) <= 1e-8 or _vec_length(target_dir) <= 1e-8:
        return (1.0, 0.0, 0.0, 0.0)

    alignment = _vec_dot(source_dir, target_dir)
    if alignment >= 1.0 - 1e-8:
        return (1.0, 0.0, 0.0, 0.0)
    if alignment <= -1.0 + 1e-8:
        hint = (1.0, 0.0, 0.0) if abs(source_dir[0]) < 0.9 else (0.0, 1.0, 0.0)
        axis = _vec_normalize(_vec_cross(source_dir, hint))
        return (0.0, axis[0], axis[1], axis[2])

    axis = _vec_cross(source_dir, target_dir)
    return normalize_quaternion_or_identity((1.0 + alignment, axis[0], axis[1], axis[2]))


def _vec_sub(
    lhs: tuple[float, float, float],
    rhs: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (lhs[0] - rhs[0], lhs[1] - rhs[1], lhs[2] - rhs[2])


def _vec_dot(
    lhs: tuple[float, float, float],
    rhs: tuple[float, float, float],
) -> float:
    return lhs[0] * rhs[0] + lhs[1] * rhs[1] + lhs[2] * rhs[2]


def _vec_cross(
    lhs: tuple[float, float, float],
    rhs: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        lhs[1] * rhs[2] - lhs[2] * rhs[1],
        lhs[2] * rhs[0] - lhs[0] * rhs[2],
        lhs[0] * rhs[1] - lhs[1] * rhs[0],
    )


def _vec_length(vector: tuple[float, float, float]) -> float:
    return math.sqrt(_vec_dot(vector, vector))


def _vec_normalize(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = _vec_length(vector)
    if length <= 1e-8:
        return (0.0, 0.0, 0.0)
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _read_float32(data: bytes, offset: int) -> float:
    import struct

    return float(struct.unpack_from("<f", data, offset)[0])


def _compute_example_skin_alignment(
    project: Any,
    world_transforms: dict[str, Any],
    skin_template: Any,
    translation_map: Any | None,
) -> _SimilarityTransform:
    from melos.blender.services.example_alignment import compute_example_skin_alignment

    return compute_example_skin_alignment(project, world_transforms, skin_template, translation_map)


def _compute_skin_reference_alignment(
    world_transforms: dict[str, Any],
    skin_template: Any,
    translation_map: Any | None,
) -> _SimilarityTransform:
    from melos.blender.services.example_alignment import compute_skin_reference_alignment

    return compute_skin_reference_alignment(world_transforms, skin_template, translation_map)


def _align_generic_humanoid(vertices: list[list[float]], similarity: _SimilarityTransform) -> list[list[float]]:
    from melos.blender.services.example_alignment import align_generic_humanoid

    return align_generic_humanoid(vertices, similarity)


def _reference_body_tail_dirs(translation_map: Any | None) -> dict[str, tuple[float, float, float]]:
    from melos.blender.services.example_alignment import reference_body_tail_dirs

    return reference_body_tail_dirs(translation_map)


def _template_world_points(project: Any) -> dict[str, tuple[float, float, float]]:
    from melos.blender.services.example_alignment import template_world_points

    return template_world_points(project)


def _bind_vertices_to_bodies(vertices: list[list[float]], bodies: list[Any], world_transforms: dict[str, Any]) -> tuple[list[list[float]], list[list[int]]]:
    from melos.blender.services.example_alignment import bind_vertices_to_bodies

    return bind_vertices_to_bodies(vertices, bodies, world_transforms)


def _resolve_resource_path(packaged_relative: str, repo_relative: str) -> Path:
    packaged = _PACKAGED_RESOURCES / packaged_relative
    if packaged.exists():
        return packaged
    return _REPO_ROOT / repo_relative


def _get_or_create_collection(scene: Any, name: str) -> Any:
    if bpy is not None and hasattr(scene, "collection"):
        existing = bpy.data.collections.get(name)
        if existing is None:
            existing = bpy.data.collections.new(name)
        root_children = getattr(scene.collection, "children", None)
        if root_children is not None:
            child_names = {getattr(child, "name", "") for child in root_children}
            if name not in child_names:
                root_children.link(existing)
        return existing

    collections = getattr(scene, "collections", None)
    if collections is None:
        return getattr(scene, "collection", scene)
    for col in collections:
        if getattr(col, "name", None) == name:
            return col
    new_col = _FakeCollectionShim(name)
    collections.append(new_col)
    return new_col



def _iter_scene_objects(scene: Any) -> list[Any]:
    scene_objects = getattr(scene, "objects", None)
    if scene_objects:
        return list(scene_objects)

    collection = getattr(scene, "collection", None)
    if collection is None:
        return []

    linked = getattr(collection, "linked", None)
    if linked is not None:
        return list(linked)

    collection_objects = getattr(collection, "objects", None)
    if collection_objects is not None:
        return list(collection_objects)

    return []



def _is_example_body_mesh_reference_object(obj: Any) -> bool:
    getter = getattr(obj, "get", None)
    if callable(getter) and getter(SKIN_REFERENCE_KIND_PROP) == SKIN_REFERENCE_KIND_BODY_MESH:
        return True
    return str(getattr(obj, "name", "")).startswith("body_")



def _example_body_mesh_reference_objects(scene: Any) -> list[Any]:
    return [obj for obj in _iter_scene_objects(scene) if _is_example_body_mesh_reference_object(obj)]



def _example_body_mesh_references_visible(scene: Any) -> bool:
    return any(not getattr(obj, "hide_viewport", False) for obj in _example_body_mesh_reference_objects(scene))



def _set_example_body_mesh_reference_visibility(scene: Any, *, visible: bool) -> int:
    body_mesh_objects = _example_body_mesh_reference_objects(scene)
    for obj in body_mesh_objects:
        if hasattr(obj, "hide_viewport"):
            obj.hide_viewport = not visible
        if hasattr(obj, "hide_render"):
            obj.hide_render = not visible
    return len(body_mesh_objects)



def _link_to_collection(collection: Any, obj: Any) -> None:
    objects = getattr(collection, "objects", None)
    if objects is None:
        return
    if hasattr(objects, "link"):
        existing_names = {getattr(existing, "name", "") for existing in objects}
        if getattr(obj, "name", None) not in existing_names:
            objects.link(obj)
        return
    if hasattr(objects, "append"):
        objects.append(obj)


class _FakeCollectionShim:
    def __init__(self, name: str) -> None:
        self.name = name
        self.objects: list[Any] = []

    def link(self, obj: Any) -> None:
        self.objects.append(obj)


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (
    MELOS_OT_validate_project,
    MELOS_OT_export_project_json,
    MELOS_OT_create_example_project,
    MELOS_OT_create_example_model_project,
    MELOS_OT_analyze_example_scale,
    MELOS_OT_toggle_example_body_mesh_references,
)

__all__ = [
    "CLASSES",
    "MELOS_OT_analyze_example_scale",
    "MELOS_OT_create_example_project",
    "MELOS_OT_create_example_model_project",
    "MELOS_OT_export_project_json",
    "MELOS_OT_toggle_example_body_mesh_references",
    "MELOS_OT_validate_project",
    "_example_body_mesh_reference_objects",
    "_example_body_mesh_references_visible",
    "_set_example_body_mesh_reference_visibility",
]

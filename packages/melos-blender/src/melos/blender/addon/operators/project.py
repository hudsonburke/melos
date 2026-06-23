"""Project-level Blender operators for melos authoring."""

from __future__ import annotations

import importlib
import math
from pathlib import Path
from typing import Any, Callable, TypedDict, cast

from melos.core.common.transforms import (
    compose_transforms,
    multiply_quaternions,
    normalize_quaternion_or_identity,
)
from melos.core.common.types import Transform
from melos.core.retarget.alignment import SimilarityTransform
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
    from melos.core.common.transforms import rotate_vector
    from melos.blender.bpy_io.skinned_import import build_weighted_mesh_object
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
            offset = rotate_vector(link_transform.rotation, point_position)
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
    body_display_scale_factors: dict[str, float] | None = None,
    display_relationship_system: Any | None = None,
    create_mesh_object: Callable[[str, Any, Any], Any] | None = None,
    attach_to_armature: bool = True,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_dirs: dict[str, tuple[float, float, float]] | None = None,
    source_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    display_scale_factor: float = 1.0,
) -> list[Any]:
    from melos.blender.bpy_io.skinned_import import (
        _build_child_map,
        _build_parent_map,
        _default_bone_tail,
        build_mesh_object,
        build_weighted_mesh_object,
    )
    from melos.core.common.transforms import rotate_vector

    anatomical_system = project.get_anatomical_system() if hasattr(project, "get_anatomical_system") else None
    if anatomical_system is None:
        return []

    asset_map = {asset.id: asset for asset in project.assets.items}
    body_index_map = {body.id: index for index, body in enumerate(anatomical_system.links)}
    body_name_map = {index: body.id for index, body in enumerate(anatomical_system.links)}
    child_map = _build_child_map(anatomical_system)
    parent_map = _build_parent_map(anatomical_system)
    # Blender should only visualize the dataclass-level retarget plan.  When a
    # display SystemModel is supplied, use its parent relationships for the
    # secondary/twist frame of reference-linked meshes while leaving raw MuJoCo
    # local offsets intact for unmapped child geometry propagation.
    relationship_parent_map = (
        _build_parent_map(display_relationship_system)
        if display_relationship_system is not None
        else None
    )
    display_transforms = _build_example_body_mesh_display_transforms(
        anatomical_system,
        world_transforms,
        child_map,
        parent_map,
        relationship_parent_map=relationship_parent_map,
        reference_body_anchors=reference_body_anchors,
        reference_body_tail_points=reference_body_tail_points,
        reference_body_tail_dirs=reference_body_tail_dirs,
        source_body_tail_points=source_body_tail_points,
        display_scale_factor=float(display_scale_factor),
        default_bone_tail=_default_bone_tail,
    )
    created: list[Any] = []
    effective_body_scale_factors = body_scale_factors or {}
    effective_body_display_scale_factors = body_display_scale_factors or {}

    for body in anatomical_system.links:
        source_transform = world_transforms.get(body.id)
        if source_transform is None:
            continue
        display_transform = display_transforms.get(body.id, source_transform)
        body_display_scale = _positive_finite_float(
            effective_body_display_scale_factors.get(body.id),
            default=float(display_scale_factor),
        )
        body_scale = effective_body_scale_factors.get(body.id, 1.0) * body_display_scale
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
                geom_rotated = rotate_vector(geom_transform['rotation'], scaled_vertex)
                geom_positioned = (
                    geom_rotated[0] + scaled_geom_translation[0],
                    geom_rotated[1] + scaled_geom_translation[1],
                    geom_rotated[2] + scaled_geom_translation[2],
                )
                rotated = rotate_vector(display_transform.rotation, geom_positioned)
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


def _positive_finite_float(value: float | None, *, default: float) -> float:
    if value is None:
        return float(default)
    resolved = float(value)
    if not math.isfinite(resolved) or resolved <= 1e-8:
        return float(default)
    return resolved


def _build_example_body_mesh_display_transforms(
    anatomical_system: Any,
    world_transforms: dict[str, Any],
    child_map: dict[str, list[str]],
    parent_map: dict[str, str],
    *,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_dirs: dict[str, tuple[float, float, float]] | None = None,
    source_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    display_scale_factor: float = 1.0,
    default_bone_tail: Callable[..., tuple[float, float, float]] | None = None,
    relationship_parent_map: dict[str, str] | None = None,
) -> dict[str, Transform]:
    link_by_id = {
        str(link.id): link
        for link in getattr(anatomical_system, "links", ()) or ()
        if getattr(link, "id", None) is not None
    }
    cache: dict[str, Transform] = {}

    def _resolve(link_id: str) -> Transform:
        cached = cache.get(link_id)
        if cached is not None:
            return cached

        source_transform = world_transforms.get(link_id)
        if source_transform is None:
            resolved = Transform.identity()
            cache[link_id] = resolved
            return resolved

        parent_id = parent_map.get(link_id)
        parent_link = link_by_id.get(parent_id or "")
        if reference_body_anchors is not None and link_id in reference_body_anchors:
            secondary_parent_map = relationship_parent_map or parent_map
            source_parent_point = _nearest_distinct_ancestor_point(
                link_id,
                source_transform.translation,
                secondary_parent_map,
                lambda ancestor_id: getattr(world_transforms.get(ancestor_id), "translation", None),
            )
            display_head = reference_body_anchors.get(link_id, source_transform.translation)
            display_parent_point = _nearest_distinct_ancestor_point(
                link_id,
                display_head,
                secondary_parent_map,
                lambda ancestor_id: _resolve(ancestor_id).translation if ancestor_id in link_by_id else None,
            )
            resolved = _example_body_mesh_display_transform(
                link_id,
                source_transform=source_transform,
                world_transforms=world_transforms,
                child_map=child_map,
                parent_map=parent_map,
                reference_body_anchors=reference_body_anchors,
                reference_body_tail_points=reference_body_tail_points,
                reference_body_tail_dirs=reference_body_tail_dirs,
                source_body_tail_points=source_body_tail_points,
                default_bone_tail=default_bone_tail,
                source_parent_point=source_parent_point,
                display_parent_point=display_parent_point,
            )
            cache[link_id] = resolved
            return resolved

        if parent_link is not None:
            parent_display = _resolve(str(parent_link.id))
            local_transform = getattr(link_by_id.get(link_id), "transform", None)
            if local_transform is not None:
                local_translation = tuple(
                    float(component) * float(display_scale_factor)
                    for component in getattr(local_transform, "translation", (0.0, 0.0, 0.0))
                )
                local_rotation = tuple(
                    float(component)
                    for component in getattr(local_transform, "rotation", (1.0, 0.0, 0.0, 0.0))
                )
                resolved = compose_transforms(
                    parent_display,
                    Transform(translation=local_translation, rotation=local_rotation),
                )
                cache[link_id] = resolved
                return resolved

        resolved = _example_body_mesh_display_transform(
            link_id,
            source_transform=source_transform,
            world_transforms=world_transforms,
            child_map=child_map,
            parent_map=parent_map,
            reference_body_anchors=reference_body_anchors,
            reference_body_tail_points=reference_body_tail_points,
            reference_body_tail_dirs=reference_body_tail_dirs,
            source_body_tail_points=source_body_tail_points,
            default_bone_tail=default_bone_tail,
        )
        cache[link_id] = resolved
        return resolved

    return {
        link_id: _resolve(link_id)
        for link_id in link_by_id
        if link_id in world_transforms
    }



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
    source_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    default_bone_tail: Callable[..., tuple[float, float, float]] | None = None,
    source_parent_point: tuple[float, float, float] | None = None,
    display_parent_point: tuple[float, float, float] | None = None,
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

    if source_body_tail_points is not None and body_id in source_body_tail_points:
        source_tail = tuple(float(value) for value in source_body_tail_points[body_id])
    else:
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
        basis_rotation = _quat_from_basis_alignment(
            source_direction,
            _vec_sub(source_parent_point, source_head) if source_parent_point is not None else None,
            display_direction,
            _vec_sub(display_parent_point, display_head) if display_parent_point is not None else None,
        )
        if basis_rotation is None:
            basis_rotation = _quat_between_vectors(source_direction, display_direction)
        rotation = normalize_quaternion_or_identity(
            multiply_quaternions(basis_rotation, rotation)
        )

    return Transform(translation=display_head, rotation=rotation)


def _nearest_distinct_ancestor_point(
    link_id: str,
    current_point: tuple[float, float, float],
    parent_map: dict[str, str],
    point_resolver: Callable[[str], tuple[float, float, float] | None],
) -> tuple[float, float, float] | None:
    visited: set[str] = set()
    ancestor_id = parent_map.get(link_id)
    while ancestor_id is not None and ancestor_id not in visited:
        visited.add(ancestor_id)
        point = point_resolver(ancestor_id)
        if point is not None and _vec_length(_vec_sub(point, current_point)) > 1e-6:
            return tuple(float(value) for value in point)
        ancestor_id = parent_map.get(ancestor_id)
    return None


def _quat_from_basis_alignment(
    source_primary: tuple[float, float, float],
    source_secondary_hint: tuple[float, float, float] | None,
    target_primary: tuple[float, float, float],
    target_secondary_hint: tuple[float, float, float] | None,
) -> tuple[float, float, float, float] | None:
    if source_secondary_hint is None or target_secondary_hint is None:
        return None

    source_primary_dir = _vec_normalize(source_primary)
    target_primary_dir = _vec_normalize(target_primary)
    if _vec_length(source_primary_dir) <= 1e-8 or _vec_length(target_primary_dir) <= 1e-8:
        return None

    source_secondary_dir = _project_onto_plane(source_secondary_hint, source_primary_dir)
    target_secondary_dir = _project_onto_plane(target_secondary_hint, target_primary_dir)
    if _vec_length(source_secondary_dir) <= 1e-8 or _vec_length(target_secondary_dir) <= 1e-8:
        return None

    source_secondary_dir = _vec_normalize(source_secondary_dir)
    target_secondary_dir = _vec_normalize(target_secondary_dir)
    source_tertiary_dir = _vec_normalize(_vec_cross(source_primary_dir, source_secondary_dir))
    target_tertiary_dir = _vec_normalize(_vec_cross(target_primary_dir, target_secondary_dir))
    if _vec_length(source_tertiary_dir) <= 1e-8 or _vec_length(target_tertiary_dir) <= 1e-8:
        return None

    source_secondary_dir = _vec_normalize(_vec_cross(source_tertiary_dir, source_primary_dir))
    target_secondary_dir = _vec_normalize(_vec_cross(target_tertiary_dir, target_primary_dir))
    source_basis = _matrix_from_columns(source_primary_dir, source_secondary_dir, source_tertiary_dir)
    target_basis = _matrix_from_columns(target_primary_dir, target_secondary_dir, target_tertiary_dir)
    return _matrix_to_quaternion(_matmul3(target_basis, _transpose3(source_basis)))


def _matrix_from_columns(
    col0: tuple[float, float, float],
    col1: tuple[float, float, float],
    col2: tuple[float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return (
        (col0[0], col1[0], col2[0]),
        (col0[1], col1[1], col2[1]),
        (col0[2], col1[2], col2[2]),
    )



def _transpose3(
    matrix: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return (
        (matrix[0][0], matrix[1][0], matrix[2][0]),
        (matrix[0][1], matrix[1][1], matrix[2][1]),
        (matrix[0][2], matrix[1][2], matrix[2][2]),
    )



def _matmul3(
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



def _matrix_to_quaternion(
    matrix: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
) -> tuple[float, float, float, float]:
    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        return normalize_quaternion_or_identity(
            (
                0.25 * scale,
                (matrix[2][1] - matrix[1][2]) / scale,
                (matrix[0][2] - matrix[2][0]) / scale,
                (matrix[1][0] - matrix[0][1]) / scale,
            )
        )
    if matrix[0][0] > matrix[1][1] and matrix[0][0] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2]) * 2.0
        return normalize_quaternion_or_identity(
            (
                (matrix[2][1] - matrix[1][2]) / scale,
                0.25 * scale,
                (matrix[0][1] + matrix[1][0]) / scale,
                (matrix[0][2] + matrix[2][0]) / scale,
            )
        )
    if matrix[1][1] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2]) * 2.0
        return normalize_quaternion_or_identity(
            (
                (matrix[0][2] - matrix[2][0]) / scale,
                (matrix[0][1] + matrix[1][0]) / scale,
                0.25 * scale,
                (matrix[1][2] + matrix[2][1]) / scale,
            )
        )
    scale = math.sqrt(1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1]) * 2.0
    return normalize_quaternion_or_identity(
        (
            (matrix[1][0] - matrix[0][1]) / scale,
            (matrix[0][2] + matrix[2][0]) / scale,
            (matrix[1][2] + matrix[2][1]) / scale,
            0.25 * scale,
        )
    )



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



def _project_onto_plane(
    vector: tuple[float, float, float],
    plane_normal: tuple[float, float, float],
) -> tuple[float, float, float]:
    normal = _vec_normalize(plane_normal)
    if _vec_length(normal) <= 1e-8:
        return vector
    scale = _vec_dot(vector, normal)
    return (
        vector[0] - normal[0] * scale,
        vector[1] - normal[1] * scale,
        vector[2] - normal[2] * scale,
    )


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




def _align_generic_humanoid(vertices: list[list[float]], similarity: SimilarityTransform) -> list[list[float]]:
    from melos.blender.services.example_alignment import align_generic_humanoid

    return align_generic_humanoid(vertices, similarity)





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

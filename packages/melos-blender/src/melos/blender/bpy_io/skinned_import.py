from __future__ import annotations

import importlib
from typing import Any, Callable

from melos.core.common.transforms import (
    axis_angle_to_quat,
    multiply_quaternions,
    quaternion_conjugate,
    rotate_vector,
    vec3_add,
    vec3_length,
    vec3_normalize,
    vec3_scale,
    vec3_sub,
)
from melos.core.common.types import Transform
from melos.core.kinematics.pose import evaluate_system_world_transforms
from melos.core.common.enums import SystemRole

try:
    bpy = importlib.import_module("bpy")
except ModuleNotFoundError:
    bpy = None


def build_armature_object(
    project: Any,
    context: Any,
    *,
    create_armature_object: Callable | None = None,
    armature_name: str = "skin_armature",
    reference_joint_positions: dict[str, tuple[float, float, float]] | None = None,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_dirs: dict[str, tuple[float, float, float]] | None = None,
    coordinate_values: dict[str, float] | None = None,
    target_system: Any | None = None,
) -> Any:
    if bpy is None and create_armature_object is None:
        raise RuntimeError("The melos add-on can only create objects inside Blender.")

    scene = context.scene
    collection = getattr(scene, "collection", scene)
    resolved_system = target_system or _resolve_skin_target_system(project)

    arm_data = _build_armature_data(
        project,
        bpy,
        target_system=resolved_system,
        reference_body_anchors=_resolve_reference_body_anchors(resolved_system, reference_body_anchors, reference_joint_positions),
        reference_body_tail_points=reference_body_tail_points,
        reference_body_tail_dirs=reference_body_tail_dirs,
        coordinate_values=coordinate_values,
    )
    if create_armature_object is not None:
        arm_obj = create_armature_object(armature_name, arm_data, collection)
    else:
        assert bpy is not None
        arm_obj = bpy.data.objects.new(armature_name, arm_data)
        collection.objects.link(arm_obj)

    return arm_obj



def build_skinned_mesh_with_armature(
    project: Any,
    vertices: list | None = None,
    faces: list | None = None,
    bone_weights: list | None = None,
    bone_indices: list | None = None,
    body_name_map: dict | None = None,
    context: Any = None,
    *,
    create_armature_object: Callable | None = None,
    create_mesh_object: Callable | None = None,
    armature_name: str = "skin_armature",
    mesh_name: str = "skin_mesh",
    reference_joint_positions: dict[str, tuple[float, float, float]] | None = None,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_dirs: dict[str, tuple[float, float, float]] | None = None,
    skin_attachment: Any | None = None,
    target_system: Any | None = None,
) -> tuple[Any, Any]:
    if bpy is None and create_armature_object is None and create_mesh_object is None:
        raise RuntimeError("The melos add-on can only create objects inside Blender.")

    attachment_coords = None
    resolved_system = target_system or _resolve_skin_target_system(project, skin_attachment=skin_attachment)
    if skin_attachment is not None:
        fit = getattr(skin_attachment, "fit", None)
        attachment_coords = dict(getattr(fit, "fit_coordinate_values", {}) or {}) if fit is not None else {}

    arm_obj = build_armature_object(
        project,
        context,
        create_armature_object=create_armature_object,
        armature_name=armature_name,
        reference_joint_positions=reference_joint_positions,
        reference_body_anchors=reference_body_anchors,
        reference_body_tail_points=reference_body_tail_points,
        reference_body_tail_dirs=reference_body_tail_dirs,
        coordinate_values=attachment_coords,
        target_system=resolved_system,
    )

    effective_vertices = vertices if vertices is not None else []
    effective_faces = faces if faces is not None else []
    effective_bone_weights = bone_weights if bone_weights is not None else []
    effective_bone_indices = bone_indices if bone_indices is not None else []
    effective_link_name_map = body_name_map if body_name_map is not None else {}

    mesh_obj = build_weighted_mesh_object(
        project,
        effective_vertices,
        effective_faces,
        effective_bone_weights,
        effective_bone_indices,
        effective_link_name_map,
        context,
        arm_obj=arm_obj,
        create_mesh_object=create_mesh_object,
        mesh_name=mesh_name,
        target_system=resolved_system,
    )

    return arm_obj, mesh_obj


def build_mesh_object(
    project: Any,
    vertices: list,
    faces: list,
    context: Any,
    *,
    create_mesh_object: Callable | None = None,
    mesh_name: str = "skin_mesh",
    edges: list | None = None,
    target_system: Any | None = None,
) -> Any:
    if bpy is None and create_mesh_object is None:
        raise RuntimeError("The melos add-on can only create objects inside Blender.")

    scene = context.scene
    collection = getattr(scene, "collection", scene)
    resolved_system = target_system or _resolve_skin_target_system(project)
    mesh_data = _build_mesh_data(vertices, faces, edges or [], [], [], {}, resolved_system, bpy)
    if create_mesh_object is not None:
        mesh_obj = create_mesh_object(mesh_name, mesh_data, collection)
    else:
        assert bpy is not None
        mesh_obj = bpy.data.objects.new(mesh_name, mesh_data)
        collection.objects.link(mesh_obj)
    return mesh_obj



def build_weighted_mesh_object(
    project: Any,
    vertices: list,
    faces: list,
    bone_weights: list,
    bone_indices: list,
    body_name_map: dict,
    context: Any,
    *,
    arm_obj: Any,
    create_mesh_object: Callable | None = None,
    mesh_name: str = "skin_mesh",
    edges: list | None = None,
    target_system: Any | None = None,
) -> Any:
    if bpy is None and create_mesh_object is None:
        raise RuntimeError("The melos add-on can only create objects inside Blender.")

    scene = context.scene
    collection = getattr(scene, "collection", scene)
    resolved_system = target_system or _resolve_skin_target_system(project)
    mesh_data = _build_mesh_data(vertices, faces, edges or [], bone_weights, bone_indices, body_name_map, resolved_system, bpy)
    if create_mesh_object is not None:
        mesh_obj = create_mesh_object(mesh_name, mesh_data, collection)
    else:
        assert bpy is not None
        mesh_obj = bpy.data.objects.new(mesh_name, mesh_data)
        collection.objects.link(mesh_obj)

    _apply_vertex_groups(mesh_obj, bone_weights, bone_indices, body_name_map, resolved_system, bpy)
    _attach_armature_modifier(mesh_obj, arm_obj, bpy)
    return mesh_obj


def _build_armature_data(
    project: Any,
    bpy_mod: Any,
    *,
    target_system: Any,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_dirs: dict[str, tuple[float, float, float]] | None = None,
    coordinate_values: dict[str, float] | None = None,
) -> Any:
    world_transforms = compute_system_link_world_transforms(target_system, coordinate_values=coordinate_values)
    child_map = _build_child_map(target_system)
    parent_map = _build_parent_map(target_system)

    if bpy_mod is not None:
        arm_data = bpy_mod.data.armatures.new("skin_armature_data")
        arm_obj_temp = bpy_mod.data.objects.new("_tmp_arm", arm_data)
        bpy_mod.context.scene.collection.objects.link(arm_obj_temp)
        for selected_obj in tuple(getattr(bpy_mod.context, "selected_objects", ())):
            selected_obj.select_set(False)
        arm_obj_temp.select_set(True)
        bpy_mod.context.view_layer.objects.active = arm_obj_temp
        if hasattr(bpy_mod.context.view_layer, "update"):
            bpy_mod.context.view_layer.update()
        if hasattr(bpy_mod.context, "temp_override"):
            with bpy_mod.context.temp_override(
                active_object=arm_obj_temp,
                object=arm_obj_temp,
                selected_objects=[arm_obj_temp],
                selected_editable_objects=[arm_obj_temp],
            ):
                bpy_mod.ops.object.mode_set(mode="EDIT")
        else:
            bpy_mod.ops.object.mode_set(mode="EDIT")
        edit_bones = arm_data.edit_bones

        bone_refs: dict[str, Any] = {}
        for link in target_system.links:
            pos = _bone_anchor_position(link.id, world_transforms, reference_body_anchors)
            bone = edit_bones.new(link.id)
            bone.head = (pos[0], pos[1], pos[2])
            tail = _default_bone_tail(
                link.id,
                world_transforms,
                child_map,
                parent_map,
                reference_body_anchors=reference_body_anchors,
                reference_body_tail_points=reference_body_tail_points,
                reference_body_tail_dirs=reference_body_tail_dirs,
            )
            bone.tail = (tail[0], tail[1], tail[2])
            bone_refs[link.id] = bone

        for link_id, parent_id in parent_map.items():
            if link_id in bone_refs and parent_id in bone_refs:
                bone_refs[link_id].parent = bone_refs[parent_id]

        if hasattr(bpy_mod.context, "temp_override"):
            with bpy_mod.context.temp_override(
                active_object=arm_obj_temp,
                object=arm_obj_temp,
                selected_objects=[arm_obj_temp],
                selected_editable_objects=[arm_obj_temp],
            ):
                bpy_mod.ops.object.mode_set(mode="OBJECT")
        else:
            bpy_mod.ops.object.mode_set(mode="OBJECT")
        bpy_mod.data.objects.remove(arm_obj_temp, do_unlink=True)
        return arm_data
    return _FakeArmatureData(
        target_system,
        world_transforms,
        child_map,
        parent_map,
        reference_body_anchors=reference_body_anchors,
        reference_body_tail_points=reference_body_tail_points,
        reference_body_tail_dirs=reference_body_tail_dirs,
    )


def compute_system_link_world_transforms(
    system: Any,
    coordinate_values: dict[str, float] | None = None,
) -> dict[str, Transform]:
    return evaluate_system_world_transforms(system, coordinate_values)


def compute_project_link_world_transforms(
    project: Any,
    coordinate_values: dict[str, float] | None = None,
) -> dict[str, Transform]:
    return compute_system_link_world_transforms(
        _resolve_skin_target_system(project),
        coordinate_values=coordinate_values,
    )


def _joint_delta(
    kind: Any,
    coordinates: list[Any],
    coordinate_values: dict[str, float],
) -> Transform:
    from melos.core.common.enums import CoordinateKind, JointKind

    if kind == JointKind.FIXED:
        return Transform.identity()

    if kind == JointKind.REVOLUTE:
        total_rotation = (1.0, 0.0, 0.0, 0.0)
        for coord in coordinates:
            if coord.kind != CoordinateKind.ROTATION:
                continue
            value = coordinate_values.get(coord.id, coord.default_value)
            total_rotation = multiply_quaternions(total_rotation, axis_angle_to_quat(coord.axis, value))
        return Transform(translation=(0.0, 0.0, 0.0), rotation=total_rotation)

    if kind == JointKind.PRISMATIC:
        tx, ty, tz = 0.0, 0.0, 0.0
        for coord in coordinates:
            if coord.kind != CoordinateKind.TRANSLATION:
                continue
            value = coordinate_values.get(coord.id, coord.default_value)
            ax, ay, az = coord.axis
            norm = (ax * ax + ay * ay + az * az) ** 0.5
            if norm > 0.0:
                ax, ay, az = ax / norm, ay / norm, az / norm
            tx += ax * value
            ty += ay * value
            tz += az * value
        return Transform(translation=(tx, ty, tz), rotation=(1.0, 0.0, 0.0, 0.0))

    return Transform.identity()


def _build_parent_map(system: Any) -> dict[str, str]:
    parent_map: dict[str, str] = {}
    link_map = {link.id: link for link in system.links}
    for joint in system.joints:
        if getattr(joint, "child_link_id", None) and getattr(joint, "parent_link_id", None):
            parent_map[joint.child_link_id] = joint.parent_link_id
    for link_id, link in link_map.items():
        if link_id in parent_map:
            continue
        parent_link = link.annotations.get("mjcf_parent_link") or link.annotations.get("mjcf_parent_body")
        if parent_link is not None and parent_link in link_map:
            parent_map[link_id] = parent_link
    return parent_map


def _build_child_map(system: Any) -> dict[str, list[str]]:
    child_map: dict[str, list[str]] = {}
    for joint in system.joints:
        if getattr(joint, "child_link_id", None) and getattr(joint, "parent_link_id", None):
            child_map.setdefault(joint.parent_link_id, []).append(joint.child_link_id)
    return child_map


def _default_bone_tail(
    link_id: str,
    world_transforms: dict[str, Transform],
    child_map: dict[str, list[str]],
    parent_map: dict[str, str],
    *,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_dirs: dict[str, tuple[float, float, float]] | None = None,
) -> tuple[float, float, float]:
    head = _bone_anchor_position(link_id, world_transforms, reference_body_anchors)
    if reference_body_tail_points is not None and link_id in reference_body_tail_points:
        tail_point = reference_body_tail_points[link_id]
        if vec3_length(vec3_sub(tail_point, head)) > 1e-6:
            return tail_point
    children = child_map.get(link_id, [])
    if children:
        child_points = [
            _bone_anchor_position(child_id, world_transforms, reference_body_anchors)
            for child_id in children
            if child_id in world_transforms
        ]
        if child_points:
            avg = (
                sum(point[0] for point in child_points) / len(child_points),
                sum(point[1] for point in child_points) / len(child_points),
                sum(point[2] for point in child_points) / len(child_points),
            )
            if vec3_length(vec3_sub(avg, head)) > 1e-6:
                return avg

    parent_id = parent_map.get(link_id)
    if parent_id is not None and parent_id in world_transforms:
        parent_point = _bone_anchor_position(parent_id, world_transforms, reference_body_anchors)
        direction = vec3_normalize(vec3_sub(head, parent_point))
        if vec3_length(direction) > 1e-6:
            return vec3_add(head, vec3_scale(direction, 0.05))

    if reference_body_tail_dirs is not None and link_id in reference_body_tail_dirs:
        direction = vec3_normalize(reference_body_tail_dirs[link_id])
        if vec3_length(direction) > 1e-6:
            return vec3_add(head, vec3_scale(direction, 0.05))

    return (head[0], head[1] + 0.05, head[2])


def _bone_anchor_position(
    link_id: str,
    world_transforms: dict[str, Transform],
    reference_body_anchors: dict[str, tuple[float, float, float]] | None,
) -> tuple[float, float, float]:
    if reference_body_anchors is not None and link_id in reference_body_anchors:
        return reference_body_anchors[link_id]
    return world_transforms[link_id].translation


def _resolve_reference_body_anchors(
    system: Any,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None,
    reference_joint_positions: dict[str, tuple[float, float, float]] | None,
) -> dict[str, tuple[float, float, float]] | None:
    if reference_body_anchors is not None:
        return reference_body_anchors
    if reference_joint_positions is None:
        return None
    link_ids = {link.id for link in system.links}
    mapping = {
        "pelvis": "Hips",
        "spine": "Spine1",
        "thorax": "Chest",
        "neck": "Neck1",
        "head": "Head",
        "left_upper_arm": "LeftArm",
        "left_forearm": "LeftForeArm",
        "right_upper_arm": "RightArm",
        "right_forearm": "RightForeArm",
        "left_thigh": "LeftLeg",
        "left_shank": "LeftShin",
        "left_foot": "LeftFoot",
        "right_thigh": "RightLeg",
        "right_shank": "RightShin",
        "right_foot": "RightFoot",
        "femur": "LeftLeg",
    }
    return {
        link_id: reference_joint_positions[joint_name]
        for link_id, joint_name in mapping.items()
        if link_id in link_ids and joint_name in reference_joint_positions
    }


def _resolve_skin_target_system(project: Any, skin_attachment: Any | None = None) -> Any:
    target_system_id = getattr(skin_attachment, "target_system_id", None) if skin_attachment is not None else None
    if target_system_id and hasattr(project, "get_system"):
        system = project.get_system(target_system_id)
        if system is not None:
            return system
    systems = getattr(project, "systems", None) or []
    anatomical_system = next((system for system in systems if system.role == SystemRole.ANATOMICAL), None)
    if anatomical_system is not None:
        return anatomical_system
    if systems:
        return systems[0]
    raise ValueError("Project does not contain any systems.")


def _build_mesh_data(
    vertices: list,
    faces: list,
    edges: list,
    bone_weights: list,
    bone_indices: list,
    body_name_map: dict,
    system: Any,
    bpy_mod: Any,
) -> Any:
    if bpy_mod is not None:
        mesh_data = bpy_mod.data.meshes.new("skin_mesh_data")
        mesh_data.from_pydata([tuple(v) for v in vertices], [tuple(edge) for edge in edges], [tuple(f) for f in faces])
        mesh_data.update()
        return mesh_data
    return _FakeMeshData(vertices, faces, bone_weights, bone_indices, body_name_map, system)


def _vertex_group_names(body_name_map: dict, system: Any) -> list[str]:
    group_names = list(dict.fromkeys(str(link_id) for link_id in body_name_map.values()))
    if group_names:
        return group_names
    return [link.id for link in system.links]



def _apply_vertex_groups(
    mesh_obj: Any,
    bone_weights: list,
    bone_indices: list,
    body_name_map: dict,
    system: Any,
    bpy_mod: Any,
) -> None:
    if bpy_mod is None:
        return

    vertex_groups = mesh_obj.vertex_groups
    for link_id in _vertex_group_names(body_name_map, system):
        vertex_groups.new(name=link_id)

    for vi, (w_row, i_row) in enumerate(zip(bone_weights, bone_indices)):
        for w, bidx in zip(w_row, i_row):
            link_id = body_name_map.get(bidx)
            if link_id is not None and link_id in vertex_groups:
                vertex_groups[link_id].add([vi], w, "REPLACE")


def _attach_armature_modifier(mesh_obj: Any, arm_obj: Any, bpy_mod: Any) -> None:
    modifiers = getattr(mesh_obj, "modifiers", None)
    if modifiers is None:
        return
    if bpy_mod is not None:
        mod = mesh_obj.modifiers.new(name="Armature", type="ARMATURE")
        mod.object = arm_obj
    else:
        mod = _FakeModifier("Armature", "ARMATURE")
        mod.object = arm_obj
        modifiers.append(mod)


class _FakeArmatureData:
    def __init__(
        self,
        system: Any,
        world_transforms: dict[str, Transform],
        child_map: dict[str, list[str]],
        parent_map: dict[str, str],
        *,
        reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
        reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
        reference_body_tail_dirs: dict[str, tuple[float, float, float]] | None = None,
    ) -> None:
        self.system = system
        self.bones: list[_FakeBone] = []

        bone_refs: dict[str, _FakeBone] = {}
        for link in system.links:
            pos = _bone_anchor_position(link.id, world_transforms, reference_body_anchors)
            tail = _default_bone_tail(
                link.id,
                world_transforms,
                child_map,
                parent_map,
                reference_body_anchors=reference_body_anchors,
                reference_body_tail_points=reference_body_tail_points,
                reference_body_tail_dirs=reference_body_tail_dirs,
            )
            bone = _FakeBone(name=link.id, head=(pos[0], pos[1], pos[2]), tail=tail)
            self.bones.append(bone)
            bone_refs[link.id] = bone

        for link_id, parent_id in parent_map.items():
            if link_id in bone_refs and parent_id in bone_refs:
                bone_refs[link_id].parent = bone_refs[parent_id]


class _FakeBone:
    def __init__(self, name: str, head: tuple, tail: tuple) -> None:
        self.name = name
        self.head = head
        self.tail = tail
        self.parent: _FakeBone | None = None


class _FakeMeshData:
    def __init__(
        self,
        vertices: list,
        faces: list,
        bone_weights: list,
        bone_indices: list,
        body_name_map: dict,
        system: Any,
    ) -> None:
        self.vertices = list(vertices)
        self.faces = list(faces)
        self.vertex_groups: dict[str, _FakeVertexGroup] = {}

        for link_id in _vertex_group_names(body_name_map, system):
            self.vertex_groups[link_id] = _FakeVertexGroup(link_id)

        for vi, (w_row, i_row) in enumerate(zip(bone_weights, bone_indices)):
            for w, bidx in zip(w_row, i_row):
                link_id = body_name_map.get(bidx)
                if link_id is not None and link_id in self.vertex_groups:
                    self.vertex_groups[link_id].add([vi], w)


class _FakeVertexGroup:
    def __init__(self, name: str) -> None:
        self.name = name
        self.weights: dict[int, float] = {}

    def add(self, indices: list[int], weight: float, mode: str = "REPLACE") -> None:
        for vi in indices:
            self.weights[vi] = weight


class _FakeModifier:
    def __init__(self, name: str, type: str) -> None:
        self.name = name
        self.type = type
        self.object: Any = None




__all__ = [
    "build_armature_object",
    "build_skinned_mesh_with_armature",
    "build_weighted_mesh_object",
    "compute_project_link_world_transforms",
    "compute_system_link_world_transforms",
]

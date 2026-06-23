from __future__ import annotations

import importlib
from typing import Any

from melos.blender.bpy_io.importer import _load_stl_mesh_data, _create_mesh_object
from melos.blender.bpy_io.skinned_import import compute_system_link_world_transforms
from melos.core.common.transforms import rotate_vector


def setup_native_fk_rig(
    arm_obj: Any,
    anatomical_system: Any,
    *,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
) -> dict[str, Any]:
    """Configure armature for native FK: one bone per link with drivers and constraints.

    Enters edit mode to align bone head/tail/roll to body local frames,
    then adds Blender drivers and LIMIT_ROTATION constraints on Euler
    channels for each joint coordinate.

    When *reference_body_anchors* is provided, bone head positions are
    taken from it (similarity-aligned space matching the skin mesh)
    instead of raw MuJoCo world positions.  The orientation (tail
    direction and roll) still comes from the MuJoCo FK rotation, which
    is coordinate-space-invariant for rigid similarity transforms.
    """
    try:
        bpy = importlib.import_module("bpy")
    except ModuleNotFoundError:
        return {}

    mathutils = importlib.import_module("mathutils")
    import json as _json

    world_transforms = compute_system_link_world_transforms(anatomical_system)
    _AXIS_TO_EULER = {
        (1.0, 0.0, 0.0): 0,  # X
        (0.0, 1.0, 0.0): 1,  # Y
        (0.0, 0.0, 1.0): 2,  # Z
    }

    def _axis_to_euler_index(axis: tuple) -> int | None:
        """Find the closest cardinal axis (X=0, Y=1, Z=2) to the given axis.

        MJCF joint axes are often close to but not exactly cardinal.
        We align each bone's local frame to the body via align_roll, so
        the joint axis in bone-local space should be near a cardinal axis.
        """
        best_idx = None
        best_dot = -1.0
        for known_axis, idx in _AXIS_TO_EULER.items():
            dot = abs(sum(a * b for a, b in zip(axis, known_axis)))
            if dot > best_dot:
                best_dot = dot
                best_idx = idx
        if best_dot < 0.5:  # reject if more than ~60° from any cardinal axis
            return None
        return best_idx

    BONE_LENGTH = 0.02
    arm_data = arm_obj.data
    context = bpy.context
    view_layer = context.view_layer

    # Deselect all, select armature
    for selected_obj in tuple(getattr(context, "selected_objects", ())):
        selected_obj.select_set(False)
    arm_obj.select_set(True)
    view_layer.objects.active = arm_obj
    if hasattr(view_layer, "update"):
        view_layer.update()

    # Enter edit mode
    if hasattr(context, "temp_override"):
        with context.temp_override(
            active_object=arm_obj,
            object=arm_obj,
            selected_objects=[arm_obj],
            selected_editable_objects=[arm_obj],
        ):
            bpy.ops.object.mode_set(mode="EDIT")
    else:
        bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = arm_data.edit_bones
    for link in anatomical_system.links:
        wt = world_transforms.get(link.id)
        if wt is None:
            continue
        bone = edit_bones.get(link.id)
        if bone is None:
            continue
        # Prefer similarity-aligned anchor positions (matching the skin mesh
        # coordinate space) over raw MuJoCo FK positions.  The anchor
        # positions are computed by applying the rest_alignment_similarity
        # to MHR joint positions, so they live in the same space as the
        # skin mesh vertices.  When no anchor is available, fall back to
        # the raw MuJoCo FK translation.
        anchor = (
            reference_body_anchors.get(link.id)
            if reference_body_anchors is not None
            else None
        )
        if anchor is not None:
            pos = anchor
        else:
            pos = wt.translation
        rot = wt.rotation
        bone.head = (pos[0], pos[1], pos[2])
        y_dir = mathutils.Quaternion((rot[0], rot[1], rot[2], rot[3])) @ mathutils.Vector((0, 1, 0))
        bone.tail = (
            pos[0] + y_dir[0] * BONE_LENGTH,
            pos[1] + y_dir[1] * BONE_LENGTH,
            pos[2] + y_dir[2] * BONE_LENGTH,
        )
        z_dir = mathutils.Quaternion((rot[0], rot[1], rot[2], rot[3])) @ mathutils.Vector((0, 0, 1))
        bone.align_roll(z_dir)

    # Exit edit mode
    if hasattr(context, "temp_override"):
        with context.temp_override(
            active_object=arm_obj,
            object=arm_obj,
            selected_objects=[arm_obj],
            selected_editable_objects=[arm_obj],
        ):
            bpy.ops.object.mode_set(mode="OBJECT")
    else:
        bpy.ops.object.mode_set(mode="OBJECT")

    # Build coordinate entries FIRST, then create properties, THEN set up drivers.
    # Properties must exist before drivers reference them.
    coord_entries: list[dict] = []

    for joint in anatomical_system.joints:
        if not joint.coordinates:
            continue
        child_link_id = joint.child_link_id

        pose_bone = arm_obj.pose.bones.get(child_link_id)
        if pose_bone is None:
            continue

        pose_bone.rotation_mode = "XYZ"

        for coord in joint.coordinates:
            euler_index = _axis_to_euler_index(coord.axis) if coord.kind.value == "rotation" else None
            is_translation = coord.kind.value == "translation"

            coord_entry: dict[str, Any] = {
                "id": coord.id,
                "joint_id": joint.id,
                "child_link_id": child_link_id,
                "kind": coord.kind.value,
                "axis": list(coord.axis),
                "euler_index": euler_index,
                "default_value": coord.default_value,
                "limits_lower": coord.limits.lower if coord.limits else None,
                "limits_upper": coord.limits.upper if coord.limits else None,
            }
            coord_entries.append(coord_entry)

    # Create ALL custom properties BEFORE setting up drivers
    for entry in coord_entries:
        prop_name = f'melos_fk_{entry["id"]}'
        arm_obj[prop_name] = entry["default_value"]
        try:
            ui = arm_obj.id_properties_ui(prop_name)
            kwargs: dict[str, object] = {"description": f'{entry["joint_id"]}: {entry["id"]}'}
            if entry["limits_lower"] is not None:
                kwargs["min"] = float(entry["limits_lower"])
            if entry["limits_upper"] is not None:
                kwargs["max"] = float(entry["limits_upper"])
            ui.update(**kwargs)
        except (AttributeError, TypeError):
            pass

    # NOW set up drivers and constraints (properties exist)
    for entry in coord_entries:
        child_link_id = entry["child_link_id"]
        pose_bone = arm_obj.pose.bones.get(child_link_id)
        if pose_bone is None:
            continue

        prop_name = f'melos_fk_{entry["id"]}'
        euler_index = entry["euler_index"]
        is_translation = entry["kind"] == "translation"

        if euler_index is not None:
            # Rotation driver
            try:
                fcurve = pose_bone.driver_add("rotation_euler", euler_index)
                driver = fcurve.driver
                driver.type = "SCRIPTED"
                var = driver.variables.new()
                var.name = "value"
                var.type = "SINGLE_PROP"
                var.targets[0].id = arm_obj
                var.targets[0].data_path = f'["{prop_name}"]'
                driver.expression = "value"
            except Exception:
                pass

            # LIMIT_ROTATION constraint
            lower = entry["limits_lower"]
            upper = entry["limits_upper"]
            if lower is not None and upper is not None:
                try:
                    constraint = pose_bone.constraints.new("LIMIT_ROTATION")
                    if euler_index == 0:
                        constraint.use_limit_x = True
                        constraint.min_x = float(lower)
                        constraint.max_x = float(upper)
                    elif euler_index == 1:
                        constraint.use_limit_y = True
                        constraint.min_y = float(lower)
                        constraint.max_y = float(upper)
                    elif euler_index == 2:
                        constraint.use_limit_z = True
                        constraint.min_z = float(lower)
                        constraint.max_z = float(upper)
                    constraint.owner_space = "LOCAL"
                    constraint.influence = 1.0
                except Exception:
                    pass

        elif is_translation:
            # Translation driver — only for axis-aligned axes
            axis = entry["axis"]
            loc_index = _axis_to_euler_index(axis)  # reuse mapping: X→0, Y→1, Z→2
            if loc_index is not None:
                try:
                    fcurve = pose_bone.driver_add("location", loc_index)
                    driver = fcurve.driver
                    driver.type = "SCRIPTED"
                    var = driver.variables.new()
                    var.name = "value"
                    var.type = "SINGLE_PROP"
                    var.targets[0].id = arm_obj
                    var.targets[0].data_path = f'["{prop_name}"]'
                    driver.expression = "value"
                except Exception:
                    pass

                # LIMIT_LOCATION constraint
                lower = entry["limits_lower"]
                upper = entry["limits_upper"]
                if lower is not None and upper is not None:
                    try:
                        constraint = pose_bone.constraints.new("LIMIT_LOCATION")
                        if loc_index == 0:
                            constraint.use_min_x = True
                            constraint.use_max_x = True
                            constraint.min_x = float(lower)
                            constraint.max_x = float(upper)
                        elif loc_index == 1:
                            constraint.use_min_y = True
                            constraint.use_max_y = True
                            constraint.min_y = float(lower)
                            constraint.max_y = float(upper)
                        elif loc_index == 2:
                            constraint.use_min_z = True
                            constraint.use_max_z = True
                            constraint.min_z = float(lower)
                            constraint.max_z = float(upper)
                        constraint.owner_space = "LOCAL"
                        constraint.influence = 1.0
                    except Exception:
                        pass

    # Build FK metadata
    fk_meta: dict[str, Any] = {
        "links": [
            {
                "id": l.id,
                "translation": list(l.transform.translation),
                "rotation": list(l.transform.rotation),
            }
            for l in anatomical_system.links
        ],
        "joints": [
            {
                "id": j.id,
                "kind": j.kind.value,
                "parent_link_id": j.parent_link_id or "",
                "child_link_id": j.child_link_id,
            }
            for j in anatomical_system.joints
        ],
        "coordinates": coord_entries,
    }

    # Store FK metadata on armature
    arm_obj["melos_fk_system"] = _json.dumps(fk_meta)

    return fk_meta


def create_rigid_body_meshes(project: Any, system: Any, arm_obj: Any, context: Any, collection: Any) -> list[Any]:
    """Create rigid body meshes parented to bones (Blender-only).

    Returns list of created mesh objects. In headless mode this returns an
    empty list — headless fallback logic lives in the caller.
    """
    try:
        bpy = importlib.import_module("bpy")
    except ModuleNotFoundError:
        return []

    project_ops = importlib.import_module("melos.blender.addon.operators.project")

    body_mesh_objects: list[Any] = []
    asset_map = {a.id: a for a in project.assets.items}
    for link in system.links:
        if not link.asset_ids:
            continue
        for asset_id in link.asset_ids:
            asset = asset_map.get(asset_id)
            if asset is None:
                continue
            if str(asset.role) != "visual":
                continue
            stl_data = _load_stl_mesh_data(asset.uri)
            if stl_data is None:
                continue
            raw_vertices, faces = stl_data
            if not raw_vertices or not faces:
                continue
            # Apply geom transform (mjcf_geom_pos, mjcf_geom_quat) to put
            # vertices in body-local space so they align with the bone.
            annotations = getattr(asset, "annotations", {}) or {}
            geom_pos = project_ops._parse_vec3_string(annotations.get("mjcf_geom_pos"))
            geom_quat = project_ops._parse_quat_string(annotations.get("mjcf_geom_quat"))
            geom_scale = project_ops._parse_scale_string(annotations.get("mjcf_geom_scale"))
            mesh_scale = project_ops._parse_scale_string(annotations.get("mjcf_mesh_scale"))
            vertices = []
            for v in raw_vertices:
                tv = project_ops._apply_scale((float(v[0]), float(v[1]), float(v[2])), mesh_scale)
                tv = project_ops._apply_scale(tv, geom_scale)
                tv = rotate_vector(geom_quat, tv)
                tv = (tv[0] + geom_pos[0], tv[1] + geom_pos[1], tv[2] + geom_pos[2])
                vertices.append(tv)
            mesh_obj = _create_mesh_object(f"body_{link.id}_{asset_id}", vertices, faces, collection)
            if mesh_obj is None:
                continue
            # Rigid parent to bone
            mesh_obj.parent = arm_obj
            mesh_obj.parent_type = "BONE"
            mesh_obj.parent_bone = link.id
            # Reset matrix_parent_inverse so mesh vertices (in body-local
            # space) are interpreted directly in the bone's local space.
            try:
                from mathutils import Matrix as _Matrix

                mesh_obj.matrix_parent_inverse = _Matrix.Identity(4)
            except (ImportError, AttributeError):
                pass
            if hasattr(mesh_obj, "display_type"):
                mesh_obj.display_type = "TEXTURED"
            if hasattr(mesh_obj, "show_in_front"):
                mesh_obj.show_in_front = True
            body_mesh_objects.append(mesh_obj)

    return body_mesh_objects


__all__ = ["setup_native_fk_rig", "create_rigid_body_meshes"]

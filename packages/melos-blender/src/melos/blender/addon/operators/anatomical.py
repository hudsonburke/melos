"""Anatomical-system entity creation operators for the melos Blender add-on."""

from __future__ import annotations

import importlib
from typing import Any, cast

from melos.core.common.types import AssetRole
from melos.core.kinematics.model import CoordinateKind, JointKind

from melos.blender.constants import (
    ASSET_ID_KEY,
    ASSET_NAME_KEY,
    ASSET_ROLE_KEY,
    ASSET_URI_KEY,
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    FRAME_LINK_ID_KEY,
    FRAME_IS_ANATOMICAL_KEY,
    JOINT_CHILD_LINK_ID_KEY,
    JOINT_CHILD_FRAME_ID_KEY,
    JOINT_COORDINATE_AXIS_KEY,
    JOINT_COORDINATE_DEFAULT_VALUE_KEY,
    JOINT_COORDINATE_ID_KEY,
    JOINT_COORDINATE_KIND_KEY,
    JOINT_COORDINATE_NAME_KEY,
    JOINT_KIND_KEY,
    JOINT_PARENT_LINK_ID_KEY,
    JOINT_PARENT_FRAME_ID_KEY,
    SCENE_SETTINGS_ATTRIBUTE,
    ANATOMICAL_LINK_ASSET_KIND,
    ANATOMICAL_LINK_KIND,
    ANATOMICAL_SITE_KIND,
    ANATOMICAL_JOINT_KIND,
)
from melos.blender.services.ids import allocate_identifier


try:
    bpy = importlib.import_module("bpy")
except ModuleNotFoundError:
    bpy = None


if bpy is not None:
    OperatorBase = bpy.types.Operator
else:
    class OperatorBase:
        pass


class MELOS_OT_create_anatomical_link(OperatorBase):
    """Create a Blender object that represents a canonical ``AnatomicalLink``."""

    bl_idname = "melos.create_anatomical_link"
    bl_label = "Create Anatomical Link"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        body_ids = _existing_entity_ids(context.scene, ANATOMICAL_LINK_KIND)
        base_name = settings.new_body_name or "Body"
        body_id = settings.new_body_id or allocate_identifier(base_name, body_ids, fallback="body")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = ANATOMICAL_LINK_KIND
        object_[ENTITY_ID_KEY] = body_id
        object_[DISPLAY_NAME_KEY] = base_name
        if not settings.anatomical_system_root_link_id:
            settings.anatomical_system_root_link_id = body_id
        _report(self, {"INFO"}, f"Created anatomical link {body_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_link_from_selected_mesh(OperatorBase):
    """Create an anatomical link and bind the active mesh as its first asset."""

    bl_idname = "melos.create_link_from_selected_mesh"
    bl_label = "Create Link From Selected Mesh"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        mesh_object = _selected_mesh_object(context)
        if mesh_object is None:
            _report(self, {"ERROR"}, "Select a mesh object before creating a body from geometry.")
            return {"CANCELLED"}

        body_ids = _existing_entity_ids(context.scene, ANATOMICAL_LINK_KIND)
        body_name = settings.new_body_name or mesh_object.name
        body_id = settings.new_body_id or allocate_identifier(body_name, body_ids, fallback="body")
        body_object = _create_empty(context, name=body_name)
        body_object[ENTITY_KIND_KEY] = ANATOMICAL_LINK_KIND
        body_object[ENTITY_ID_KEY] = body_id
        body_object[DISPLAY_NAME_KEY] = body_name

        _tag_mesh_as_link_asset(
            context,
            mesh_object=mesh_object,
            body_object=body_object,
            link_id=body_id,
            asset_role=settings.mesh_asset_role or AssetRole.VISUAL.value,
        )

        if not settings.anatomical_system_root_link_id:
            settings.anatomical_system_root_link_id = body_id

        _report(
            self,
            {"INFO"},
            f"Created anatomical link {body_id!r} from mesh {mesh_object.name!r}.",
        )
        return {"FINISHED"}


class MELOS_OT_assign_selected_mesh_to_body(OperatorBase):
    """Assign the selected mesh as an asset of an existing anatomical link."""

    bl_idname = "melos.assign_selected_mesh_to_body"
    bl_label = "Assign Selected Mesh To Body"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        mesh_object = _selected_mesh_object(context)
        if mesh_object is None:
            _report(self, {"ERROR"}, "Select a mesh object before assigning it to a body.")
            return {"CANCELLED"}

        body_object = _resolve_target_link_object(context, settings.mesh_target_link_id)
        if body_object is None:
            _report(
                self,
                {"ERROR"},
                "Set Target Link ID or select an anatomical link alongside the mesh.",
            )
            return {"CANCELLED"}

        link_id = str(cast(Any, body_object).get(ENTITY_ID_KEY, ""))
        if not link_id:
            _report(self, {"ERROR"}, "Resolved link is missing a melos link ID.")
            return {"CANCELLED"}

        _tag_mesh_as_link_asset(
            context,
            mesh_object=mesh_object,
            body_object=body_object,
            link_id=link_id,
            asset_role=settings.mesh_asset_role or AssetRole.VISUAL.value,
        )
        _report(
            self,
            {"INFO"},
            f"Assigned mesh {mesh_object.name!r} to anatomical link {link_id!r}.",
        )
        return {"FINISHED"}


class MELOS_OT_set_selected_mesh_asset_role(OperatorBase):
    """Update the selected mesh asset role for scene-to-core export."""

    bl_idname = "melos.set_selected_mesh_asset_role"
    bl_label = "Apply Role To Selected Mesh"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        mesh_object = _selected_mesh_object(context)
        if mesh_object is None:
            _report(self, {"ERROR"}, "Select a mesh object before applying an asset role.")
            return {"CANCELLED"}

        mesh_object[ASSET_ROLE_KEY] = settings.mesh_asset_role or AssetRole.VISUAL.value
        mesh_object[ASSET_NAME_KEY] = mesh_object.get(ASSET_NAME_KEY, mesh_object.name)
        mesh_object[ASSET_URI_KEY] = mesh_object.get(
            ASSET_URI_KEY,
            f"blender://object/{mesh_object.name}",
        )

        if mesh_object.get(ENTITY_KIND_KEY) == ANATOMICAL_LINK_ASSET_KIND and not mesh_object.get(ASSET_ID_KEY):
            mesh_object[ASSET_ID_KEY] = allocate_identifier(
                f"{mesh_object.get(ENTITY_ID_KEY, 'asset')}_{settings.mesh_asset_role}",
                _existing_asset_ids(context.scene),
                fallback="asset",
            )

        _report(
            self,
            {"INFO"},
            f"Applied asset role {mesh_object[ASSET_ROLE_KEY]!r} to mesh {mesh_object.name!r}.",
        )
        return {"FINISHED"}


class MELOS_OT_create_anatomical_site(OperatorBase):
    """Create a Blender object that represents a canonical ``AnatomicalSite``."""

    bl_idname = "melos.create_anatomical_site"
    bl_label = "Create Anatomical Site"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        frame_ids = _existing_entity_ids(context.scene, ANATOMICAL_SITE_KIND)
        base_name = settings.new_frame_name or "Frame"
        frame_id = settings.new_frame_id or allocate_identifier(base_name, frame_ids, fallback="frame")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = ANATOMICAL_SITE_KIND
        object_[ENTITY_ID_KEY] = frame_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[FRAME_LINK_ID_KEY] = settings.frame_body_id or _selected_link_id(context)
        object_[FRAME_IS_ANATOMICAL_KEY] = bool(settings.frame_is_anatomical)

        parent_body = _selected_link_object(context)
        if parent_body is not None:
            object_.parent = parent_body
            object_.matrix_parent_inverse = parent_body.matrix_world.inverted()

        _report(self, {"INFO"}, f"Created anatomical site {frame_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_anatomical_joint(OperatorBase):
    """Create a Blender object that represents a canonical ``AnatomicalJoint``."""

    bl_idname = "melos.create_anatomical_joint"
    bl_label = "Create Anatomical Joint"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        joint_ids = _existing_entity_ids(context.scene, ANATOMICAL_JOINT_KIND)
        base_name = settings.new_joint_name or "Joint"
        joint_id = settings.new_joint_id or allocate_identifier(base_name, joint_ids, fallback="joint")
        coordinate_id = settings.coordinate_id or allocate_identifier(
            settings.coordinate_name or f"{base_name} Coordinate",
            _existing_coordinate_ids(context.scene),
            fallback="coordinate",
        )
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = ANATOMICAL_JOINT_KIND
        object_[ENTITY_ID_KEY] = joint_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[JOINT_KIND_KEY] = settings.joint_kind or JointKind.REVOLUTE.value
        object_[JOINT_PARENT_FRAME_ID_KEY] = settings.joint_parent_frame_id
        object_[JOINT_CHILD_FRAME_ID_KEY] = settings.joint_child_frame_id
        object_[JOINT_PARENT_LINK_ID_KEY] = settings.joint_parent_link_id
        object_[JOINT_CHILD_LINK_ID_KEY] = settings.joint_child_link_id
        object_[JOINT_COORDINATE_ID_KEY] = coordinate_id
        object_[JOINT_COORDINATE_NAME_KEY] = settings.coordinate_name or coordinate_id
        object_[JOINT_COORDINATE_KIND_KEY] = settings.coordinate_kind or CoordinateKind.ROTATION.value
        object_[JOINT_COORDINATE_AXIS_KEY] = (
            settings.coordinate_axis_x,
            settings.coordinate_axis_y,
            settings.coordinate_axis_z,
        )
        object_[JOINT_COORDINATE_DEFAULT_VALUE_KEY] = settings.coordinate_default_value
        _report(self, {"INFO"}, f"Created anatomical joint {joint_id!r}.")
        return {"FINISHED"}


def _create_empty(context, *, name: str):
    if bpy is None:  # pragma: no cover - Blender-only path
        raise RuntimeError("The melos add-on can only create objects inside Blender.")
    object_ = bpy.data.objects.new(name, None)
    object_.empty_display_type = "PLAIN_AXES"
    context.collection.objects.link(object_)
    object_.location = context.scene.cursor.location
    return object_


def _existing_entity_ids(scene, entity_kind: str) -> set[str]:
    return {
        str(object_.get(ENTITY_ID_KEY))
        for object_ in scene.objects
        if object_.get(ENTITY_KIND_KEY) == entity_kind and object_.get(ENTITY_ID_KEY)
    }


def _existing_coordinate_ids(scene) -> set[str]:
    return {
        str(object_.get(JOINT_COORDINATE_ID_KEY))
        for object_ in scene.objects
        if object_.get(ENTITY_KIND_KEY) == ANATOMICAL_JOINT_KIND
        and object_.get(JOINT_COORDINATE_ID_KEY)
    }


def _existing_asset_ids(scene) -> set[str]:
    return {
        str(object_.get(ASSET_ID_KEY))
        for object_ in scene.objects
        if object_.get(ASSET_ID_KEY)
    }


def _link_object_by_id(scene, link_id: str) -> object | None:
    for object_ in scene.objects:
        if (
            object_.get(ENTITY_KIND_KEY) == ANATOMICAL_LINK_KIND
            and str(object_.get(ENTITY_ID_KEY, "")) == link_id
        ):
            return object_
    return None


def _selected_link_object(context):
    object_ = getattr(context, "active_object", None)
    if object_ is None:
        return None
    if object_.get(ENTITY_KIND_KEY) != ANATOMICAL_LINK_KIND:
        return None
    return object_


def _resolve_target_link_object(context, explicit_link_id: str) -> object | None:
    if explicit_link_id:
        return _link_object_by_id(context.scene, explicit_link_id)

    selected_objects = getattr(context, "selected_objects", ())
    for object_ in selected_objects:
        if getattr(object_, "type", None) == "MESH":
            continue
        if object_.get(ENTITY_KIND_KEY) == ANATOMICAL_LINK_KIND:
            return object_

    return _selected_link_object(context)


def _selected_mesh_object(context):
    object_ = getattr(context, "active_object", None)
    if object_ is None:
        return None
    if getattr(object_, "type", None) != "MESH":
        return None
    return object_


def _tag_mesh_as_link_asset(
    context,
    *,
    mesh_object,
    body_object,
    link_id: str,
    asset_role: str,
) -> None:
    mesh_object.parent = body_object
    mesh_object.matrix_parent_inverse = body_object.matrix_world.inverted()
    mesh_object[ENTITY_KIND_KEY] = ANATOMICAL_LINK_ASSET_KIND
    mesh_object[ENTITY_ID_KEY] = link_id
    if not mesh_object.get(ASSET_ID_KEY):
        mesh_object[ASSET_ID_KEY] = allocate_identifier(
            f"{link_id}_{asset_role}",
            _existing_asset_ids(context.scene),
            fallback="asset",
        )
    mesh_object[ASSET_NAME_KEY] = mesh_object.get(ASSET_NAME_KEY, mesh_object.name)
    mesh_object[ASSET_ROLE_KEY] = asset_role
    mesh_object[ASSET_URI_KEY] = mesh_object.get(
        ASSET_URI_KEY,
        f"blender://object/{mesh_object.name}",
    )


def _selected_link_id(context) -> str:
    object_ = _selected_link_object(context)
    if object_ is None:
        return ""
    return str(object_.get(ENTITY_ID_KEY, ""))


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (
    MELOS_OT_assign_selected_mesh_to_body,
    MELOS_OT_create_link_from_selected_mesh,
    MELOS_OT_set_selected_mesh_asset_role,
    MELOS_OT_create_anatomical_link,
    MELOS_OT_create_anatomical_site,
    MELOS_OT_create_anatomical_joint,
)

__all__ = [
    "CLASSES",
    "MELOS_OT_assign_selected_mesh_to_body",
    "MELOS_OT_create_link_from_selected_mesh",
    "MELOS_OT_set_selected_mesh_asset_role",
    "MELOS_OT_create_anatomical_link",
    "MELOS_OT_create_anatomical_site",
    "MELOS_OT_create_anatomical_joint",
]

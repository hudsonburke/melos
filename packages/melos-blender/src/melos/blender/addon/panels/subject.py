"""Subject authoring panels for the melos Blender add-on."""

from __future__ import annotations

import importlib
from typing import Any, cast

from melos.blender.constants import ADDON_NAME, SCENE_SETTINGS_ATTRIBUTE


try:
    bpy = importlib.import_module("bpy")
except ModuleNotFoundError:
    bpy = None


if bpy is not None:
    PanelBase = bpy.types.Panel
else:
    class PanelBase:
        pass


class MELOS_PT_subject(PanelBase):
    """Subject metadata and entity creation controls."""

    bl_label = "Subject"
    bl_idname = "MELOS_PT_subject"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        layout.operator("melos.import_project")
        layout.operator("melos.create_example_project")
        layout.operator("melos.create_example_model_project")
        layout.separator()
        layout.prop(settings, "anatomical_system_id")
        layout.prop(settings, "anatomical_system_name")
        layout.prop(settings, "anatomical_system_description")
        layout.prop(settings, "anatomical_species")
        layout.prop(settings, "anatomical_system_root_link_id")
        layout.separator()


class MELOS_PT_subject_add_body(PanelBase):
    bl_label = "Add Body"
    bl_idname = "MELOS_PT_subject_add_body"
    bl_parent_id = "MELOS_PT_subject"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_body_name")
        box.prop(settings, "new_body_id")
        box.prop(settings, "mesh_asset_role")
        box.prop(settings, "mesh_target_link_id")
        box.operator("melos.create_anatomical_link")
        box.operator("melos.create_body_from_selected_mesh")
        box.operator("melos.assign_selected_mesh_to_body")
        box.operator("melos.set_selected_mesh_asset_role")


class MELOS_PT_subject_add_frame(PanelBase):
    bl_label = "Add Frame"
    bl_idname = "MELOS_PT_subject_add_frame"
    bl_parent_id = "MELOS_PT_subject"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_frame_name")
        box.prop(settings, "new_frame_id")
        box.prop(settings, "frame_body_id")
        box.prop(settings, "frame_is_anatomical")
        box.operator("melos.create_anatomical_site")


class MELOS_PT_subject_add_joint(PanelBase):
    bl_label = "Add Joint"
    bl_idname = "MELOS_PT_subject_add_joint"
    bl_parent_id = "MELOS_PT_subject"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_joint_name")
        box.prop(settings, "new_joint_id")
        box.prop(settings, "joint_kind")
        box.prop(settings, "joint_parent_frame_id")
        box.prop(settings, "joint_child_frame_id")
        box.prop(settings, "joint_parent_link_id")
        box.prop(settings, "joint_child_link_id")
        box.prop(settings, "coordinate_name")
        box.prop(settings, "coordinate_id")
        box.prop(settings, "coordinate_kind")
        row = box.row(align=True)
        row.prop(settings, "coordinate_axis_x")
        row.prop(settings, "coordinate_axis_y")
        row.prop(settings, "coordinate_axis_z")
        box.prop(settings, "coordinate_default_value")
        box.operator("melos.create_anatomical_joint")


class MELOS_PT_subject_add_landmark(PanelBase):
    bl_label = "Add Landmark"
    bl_idname = "MELOS_PT_subject_add_landmark"
    bl_parent_id = "MELOS_PT_subject"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_landmark_name")
        box.prop(settings, "new_landmark_id")
        box.prop(settings, "landmark_body_id")
        box.prop(settings, "landmark_frame_id")
        box.operator("melos.create_landmark")


class MELOS_PT_subject_add_muscle_path(PanelBase):
    bl_label = "Add Muscle Path"
    bl_idname = "MELOS_PT_subject_add_muscle_path"
    bl_parent_id = "MELOS_PT_subject"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "muscle_id")
        box.prop(settings, "muscle_name")
        box.separator()
        box.prop(settings, "new_path_point_name")
        box.prop(settings, "new_path_point_id")
        box.prop(settings, "path_point_kind")
        box.prop(settings, "path_point_link_id")
        box.prop(settings, "path_point_site_id")
        box.prop(settings, "path_point_order")
        box.operator("melos.create_muscle_path_point")


class MELOS_PT_subject_add_wrap(PanelBase):
    bl_label = "Add Wrap Geometry"
    bl_idname = "MELOS_PT_subject_add_wrap"
    bl_parent_id = "MELOS_PT_subject"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_wrap_name")
        box.prop(settings, "new_wrap_id")
        box.prop(settings, "wrap_kind")
        box.prop(settings, "wrap_link_id")
        box.prop(settings, "wrap_site_id")
        box.prop(settings, "wrap_radius")
        box.prop(settings, "wrap_height")
        box.operator("melos.create_wrap_geometry")


CLASSES = (
    MELOS_PT_subject,
    MELOS_PT_subject_add_body,
    MELOS_PT_subject_add_frame,
    MELOS_PT_subject_add_joint,
    MELOS_PT_subject_add_landmark,
    MELOS_PT_subject_add_muscle_path,
    MELOS_PT_subject_add_wrap,
)

__all__ = ["CLASSES"]

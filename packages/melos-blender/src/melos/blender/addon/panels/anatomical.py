"""Anatomical system authoring panels for the melos Blender add-on."""

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
    """Anatomical system metadata and entity creation controls."""

    bl_label = "Anatomical System"
    bl_idname = "MELOS_PT_subject"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        layout.prop(settings, "anatomical_system_id")
        layout.prop(settings, "anatomical_system_name")
        layout.prop(settings, "anatomical_system_description")
        layout.prop(settings, "anatomical_species")
        layout.prop(settings, "anatomical_system_root_link_id")
        layout.separator()

        box = layout.box()
        box.label(text="Create Body")
        box.prop(settings, "new_body_name")
        box.prop(settings, "new_body_id")
        box.prop(settings, "mesh_asset_role")
        box.prop(settings, "mesh_target_link_id")
        box.operator("melos.create_anatomical_link")
        box.operator("melos.create_body_from_selected_mesh")
        box.operator("melos.assign_selected_mesh_to_body")
        box.operator("melos.set_selected_mesh_asset_role")

        box = layout.box()
        box.label(text="Create Frame")
        box.prop(settings, "new_frame_name")
        box.prop(settings, "new_frame_id")
        box.prop(settings, "frame_body_id")
        box.prop(settings, "frame_is_anatomical")
        box.operator("melos.create_anatomical_site")

        box = layout.box()
        box.label(text="Create Joint")
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


CLASSES = (MELOS_PT_subject,)

__all__ = ["CLASSES", "MELOS_PT_subject"]

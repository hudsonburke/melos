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


class MELOS_PT_muscle(PanelBase):

    bl_label = "Muscles"
    bl_idname = "MELOS_PT_muscle"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        layout.prop(settings, "muscle_id")
        layout.prop(settings, "muscle_name")
        layout.separator()

        box = layout.box()
        box.label(text="Create Path Point")
        box.prop(settings, "new_path_point_name")
        box.prop(settings, "new_path_point_id")
        box.prop(settings, "path_point_kind")
        box.prop(settings, "path_point_link_id")
        box.prop(settings, "path_point_site_id")
        box.prop(settings, "path_point_order")
        box.operator("melos.create_muscle_path_point")

        box = layout.box()
        box.label(text="Create Wrap Geometry")
        box.prop(settings, "new_wrap_name")
        box.prop(settings, "new_wrap_id")
        box.prop(settings, "wrap_kind")
        box.prop(settings, "wrap_link_id")
        box.prop(settings, "wrap_site_id")
        box.prop(settings, "wrap_radius")
        box.prop(settings, "wrap_height")
        box.operator("melos.create_wrap_geometry")


CLASSES = (MELOS_PT_muscle,)

__all__ = ["CLASSES", "MELOS_PT_muscle"]

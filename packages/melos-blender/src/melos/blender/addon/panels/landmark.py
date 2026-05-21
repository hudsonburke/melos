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


class MELOS_PT_landmark(PanelBase):
    bl_label = "Landmarks"
    bl_idname = "MELOS_PT_landmark"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)

        box = layout.box()
        box.label(text="Create Landmark")
        box.prop(settings, "new_landmark_name")
        box.prop(settings, "new_landmark_id")
        box.prop(settings, "landmark_body_id")
        box.prop(settings, "landmark_frame_id")
        box.operator("melos.create_landmark")


CLASSES = (MELOS_PT_landmark,)

__all__ = ["CLASSES", "MELOS_PT_landmark"]

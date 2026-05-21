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


class MELOS_PT_assembly(PanelBase):
    bl_label = "Assembly"
    bl_idname = "MELOS_PT_assembly"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        layout.prop(settings, "assembly_id")
        layout.prop(settings, "assembly_name")
        layout.separator()

        box = layout.box()
        box.label(text="Create Attachment")
        box.prop(settings, "new_attachment_name")
        box.prop(settings, "new_attachment_id")
        box.prop(settings, "attachment_device_id")
        box.prop(settings, "attachment_interface_id")
        box.prop(settings, "attachment_anatomical_site_id")
        box.operator("melos.create_attachment")


CLASSES = (MELOS_PT_assembly,)

__all__ = ["CLASSES", "MELOS_PT_assembly"]

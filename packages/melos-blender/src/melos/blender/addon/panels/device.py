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


class MELOS_PT_device(PanelBase):
    bl_label = "Device"
    bl_idname = "MELOS_PT_device"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        layout.prop(settings, "device_id")
        layout.prop(settings, "device_name")
        layout.prop(settings, "device_root_link_id")
        layout.separator()

        box = layout.box()
        box.label(text="Create Link")
        box.prop(settings, "new_device_link_name")
        box.prop(settings, "new_device_link_id")
        box.operator("melos.create_device_link")

        box = layout.box()
        box.label(text="Create Frame")
        box.prop(settings, "new_device_frame_name")
        box.prop(settings, "new_device_frame_id")
        box.prop(settings, "device_frame_link_id")
        box.operator("melos.create_device_frame")

        box = layout.box()
        box.label(text="Create Joint")
        box.prop(settings, "new_device_joint_name")
        box.prop(settings, "new_device_joint_id")
        box.prop(settings, "device_joint_kind")
        box.prop(settings, "device_joint_parent_link_id")
        box.prop(settings, "device_joint_child_link_id")
        box.prop(settings, "device_joint_parent_frame_id")
        box.prop(settings, "device_joint_child_frame_id")
        box.prop(settings, "device_coordinate_name")
        box.prop(settings, "device_coordinate_id")
        box.prop(settings, "device_coordinate_kind")
        row = box.row(align=True)
        row.prop(settings, "device_coordinate_axis_x")
        row.prop(settings, "device_coordinate_axis_y")
        row.prop(settings, "device_coordinate_axis_z")
        box.operator("melos.create_device_joint")

        box = layout.box()
        box.label(text="Create Sensor")
        box.prop(settings, "new_device_sensor_name")
        box.prop(settings, "new_device_sensor_id")
        box.prop(settings, "device_sensor_kind")
        box.prop(settings, "device_sensor_frame_id")
        box.prop(settings, "device_sensor_link_id")
        box.operator("melos.create_device_sensor")

        box = layout.box()
        box.label(text="Create Actuator")
        box.prop(settings, "new_device_actuator_name")
        box.prop(settings, "new_device_actuator_id")
        box.prop(settings, "device_actuator_kind")
        box.prop(settings, "device_actuator_joint_id")
        box.prop(settings, "device_actuator_coordinate_id")
        box.operator("melos.create_device_actuator")


CLASSES = (MELOS_PT_device,)

__all__ = ["CLASSES", "MELOS_PT_device"]

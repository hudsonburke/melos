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


class MELOS_PT_device_generate_part(PanelBase):
    bl_label = "Generate Part"
    bl_idname = "MELOS_PT_device_generate_part"
    bl_parent_id = "MELOS_PT_device"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "part_target_segment")
        box.prop(settings, "part_type")
        box.prop(settings, "part_limb_circumference")
        box.prop(settings, "part_coverage")
        box.prop(settings, "part_width")
        box.prop(settings, "part_wall_thickness")
        box.prop(settings, "part_padding_thickness")
        box.operator("melos.generate_part")


class MELOS_PT_device_add_link(PanelBase):
    bl_label = "Add Link"
    bl_idname = "MELOS_PT_device_add_link"
    bl_parent_id = "MELOS_PT_device"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_device_link_name")
        box.prop(settings, "new_device_link_id")
        box.operator("melos.create_device_link")


class MELOS_PT_device_add_frame(PanelBase):
    bl_label = "Add Frame"
    bl_idname = "MELOS_PT_device_add_frame"
    bl_parent_id = "MELOS_PT_device"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_device_frame_name")
        box.prop(settings, "new_device_frame_id")
        box.prop(settings, "device_frame_link_id")
        box.operator("melos.create_device_frame")


class MELOS_PT_device_add_joint(PanelBase):
    bl_label = "Add Joint"
    bl_idname = "MELOS_PT_device_add_joint"
    bl_parent_id = "MELOS_PT_device"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
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


class MELOS_PT_device_add_sensor(PanelBase):
    bl_label = "Add Sensor"
    bl_idname = "MELOS_PT_device_add_sensor"
    bl_parent_id = "MELOS_PT_device"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_device_sensor_name")
        box.prop(settings, "new_device_sensor_id")
        box.prop(settings, "device_sensor_kind")
        box.prop(settings, "device_sensor_frame_id")
        box.prop(settings, "device_sensor_link_id")
        box.operator("melos.create_device_sensor")


class MELOS_PT_device_add_actuator(PanelBase):
    bl_label = "Add Actuator"
    bl_idname = "MELOS_PT_device_add_actuator"
    bl_parent_id = "MELOS_PT_device"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_device_actuator_name")
        box.prop(settings, "new_device_actuator_id")
        box.prop(settings, "device_actuator_kind")
        box.prop(settings, "device_actuator_joint_id")
        box.prop(settings, "device_actuator_coordinate_id")
        box.operator("melos.create_device_actuator")


class MELOS_PT_device_cable_routing(PanelBase):
    bl_label = "Cable Routing"
    bl_idname = "MELOS_PT_device_cable_routing"
    bl_parent_id = "MELOS_PT_device"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "new_cable_route_name")
        box.prop(settings, "new_cable_route_id")
        box.prop(settings, "cable_actuator_id")
        box.prop(settings, "cable_route_node_kind")
        box.prop(settings, "cable_route_order")
        box.prop(settings, "cable_route_site_id")
        box.prop(settings, "cable_route_geometry_id")
        box.prop(settings, "cable_route_side_site_id")
        box.operator("melos.create_cable_route_point")
        box.operator("melos.update_cable_visualization")


class MELOS_PT_device_attach(PanelBase):
    bl_label = "Attach to Subject"
    bl_idname = "MELOS_PT_device_attach"
    bl_parent_id = "MELOS_PT_device"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        box = layout.box()
        box.prop(settings, "assembly_id")
        box.prop(settings, "assembly_name")
        box.separator()
        box.prop(settings, "new_attachment_name")
        box.prop(settings, "new_attachment_id")
        box.prop(settings, "attachment_device_id")
        box.prop(settings, "attachment_interface_id")
        box.prop(settings, "attachment_anatomical_site_id")
        box.operator("melos.create_attachment")


CLASSES = (
    MELOS_PT_device,
    MELOS_PT_device_generate_part,
    MELOS_PT_device_add_link,
    MELOS_PT_device_add_frame,
    MELOS_PT_device_add_joint,
    MELOS_PT_device_add_sensor,
    MELOS_PT_device_add_actuator,
    MELOS_PT_device_cable_routing,
    MELOS_PT_device_attach,
)

__all__ = ["CLASSES"]

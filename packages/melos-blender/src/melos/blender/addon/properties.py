"""Blender property groups used by the melos add-on."""

from __future__ import annotations

import importlib

from melos.core.common.enums import AssetRole
from melos.core.common.units import DEFAULT_GRAVITY
from melos.core.kinematics.enums import CoordinateKind, JointKind
from melos.core.actuator.muscles.enums import MusclePathPointKind, WrapGeometryKind
from melos.core.system.enums import ActuatorKind, SensorKind


def _fallback_property(**_: object) -> None:
    return None


try:
    bpy = importlib.import_module("bpy")
    bpy_props = importlib.import_module("bpy.props")
except ModuleNotFoundError:
    bpy = None
    bpy_props = None


if bpy is not None:
    PropertyGroupBase = bpy.types.PropertyGroup
else:
    class PropertyGroupBase:
        pass

StringProperty = getattr(bpy_props, "StringProperty", _fallback_property)
BoolProperty = getattr(bpy_props, "BoolProperty", _fallback_property)
FloatProperty = getattr(bpy_props, "FloatProperty", _fallback_property)
EnumProperty = getattr(bpy_props, "EnumProperty", _fallback_property)


_JOINT_KIND_ITEMS = [(kind.value, kind.name.title(), "") for kind in JointKind]
_COORDINATE_KIND_ITEMS = [(kind.value, kind.name.title(), "") for kind in CoordinateKind]
_ASSET_ROLE_ITEMS = [(role.value, role.name.title(), "") for role in AssetRole]
_SENSOR_KIND_ITEMS = [(kind.value, kind.name.title(), "") for kind in SensorKind]
_ACTUATOR_KIND_ITEMS = [(kind.value, kind.name.title(), "") for kind in ActuatorKind]
_MUSCLE_PATH_POINT_KIND_ITEMS = [(kind.value, kind.name.title(), "") for kind in MusclePathPointKind]
_WRAP_GEOMETRY_KIND_ITEMS = [(kind.value, kind.name.title(), "") for kind in WrapGeometryKind]


class MELOSAddonSettings(PropertyGroupBase):
    """Scene-scoped settings that front the canonical melos project model."""


MELOSAddonSettings.__annotations__ = {
    "project_id": StringProperty(name="Project ID", default="project"),
    "project_name": StringProperty(name="Project Name", default="untitled"),
    "project_description": StringProperty(name="Description", default=""),
    "created_by": StringProperty(name="Created By", default=""),
    "anatomical_system_id": StringProperty(name="Anatomical System ID", default="anatomical"),
    "anatomical_system_name": StringProperty(name="Anatomical System Name", default="anatomical"),
    "anatomical_system_description": StringProperty(name="Anatomical System Description", default=""),
    "anatomical_species": StringProperty(name="Species", default=""),
    "anatomical_system_root_link_id": StringProperty(name="Root Link ID", default=""),
    "time_step": FloatProperty(name="Time Step", default=0.001, min=1e-6),
    "duration": FloatProperty(name="Duration", default=0.0, min=0.0),
    "gravity_x": FloatProperty(name="Gravity X", default=DEFAULT_GRAVITY[0]),
    "gravity_y": FloatProperty(name="Gravity Y", default=DEFAULT_GRAVITY[1]),
    "gravity_z": FloatProperty(name="Gravity Z", default=DEFAULT_GRAVITY[2]),
    "new_body_name": StringProperty(name="Body Name", default="Body"),
    "new_body_id": StringProperty(name="Link ID", default=""),
    "mesh_asset_role": EnumProperty(
        name="Mesh Role",
        items=_ASSET_ROLE_ITEMS,
        default=AssetRole.VISUAL.value,
    ),
    "mesh_target_link_id": StringProperty(name="Target Link ID", default=""),
    "new_frame_name": StringProperty(name="Frame Name", default="Frame"),
    "new_frame_id": StringProperty(name="Site ID", default=""),
    "frame_body_id": StringProperty(name="Frame Link ID", default=""),
    "frame_is_anatomical": BoolProperty(name="Anatomical", default=True),
    "new_joint_name": StringProperty(name="Joint Name", default="Joint"),
    "new_joint_id": StringProperty(name="Joint ID", default=""),
    "joint_kind": EnumProperty(
        name="Joint Kind",
        items=_JOINT_KIND_ITEMS,
        default=JointKind.REVOLUTE.value,
    ),
    "joint_parent_frame_id": StringProperty(name="Parent Site ID", default=""),
    "joint_child_frame_id": StringProperty(name="Child Site ID", default=""),
    "joint_parent_link_id": StringProperty(name="Parent Link ID", default=""),
    "joint_child_link_id": StringProperty(name="Child Link ID", default=""),
    "coordinate_name": StringProperty(name="Coordinate Name", default="Coordinate"),
    "coordinate_id": StringProperty(name="Coordinate ID", default=""),
    "coordinate_kind": EnumProperty(
        name="Coordinate Kind",
        items=_COORDINATE_KIND_ITEMS,
        default=CoordinateKind.ROTATION.value,
    ),
    "coordinate_axis_x": FloatProperty(name="Axis X", default=1.0),
    "coordinate_axis_y": FloatProperty(name="Axis Y", default=0.0),
    "coordinate_axis_z": FloatProperty(name="Axis Z", default=0.0),
    "coordinate_default_value": FloatProperty(name="Default Value", default=0.0),
    "export_path": StringProperty(
        name="Export Path",
        default="melos_project.json",
        subtype="FILE_PATH",
    ),
    "device_id": StringProperty(name="Device ID", default="device"),
    "device_name": StringProperty(name="Device Name", default="device"),
    "device_root_link_id": StringProperty(name="Root Link ID", default=""),
    "new_device_link_name": StringProperty(name="Link Name", default="Link"),
    "new_device_link_id": StringProperty(name="Link ID", default=""),
    "new_device_frame_name": StringProperty(name="Frame Name", default="Frame"),
    "new_device_frame_id": StringProperty(name="Site ID", default=""),
    "device_frame_link_id": StringProperty(name="Frame Link ID", default=""),
    "new_device_joint_name": StringProperty(name="Joint Name", default="Joint"),
    "new_device_joint_id": StringProperty(name="Joint ID", default=""),
    "device_joint_kind": EnumProperty(name="Joint Kind", items=_JOINT_KIND_ITEMS, default=JointKind.REVOLUTE.value),
    "device_joint_parent_link_id": StringProperty(name="Parent Link ID", default=""),
    "device_joint_child_link_id": StringProperty(name="Child Link ID", default=""),
    "device_joint_parent_frame_id": StringProperty(name="Parent Site ID", default=""),
    "device_joint_child_frame_id": StringProperty(name="Child Site ID", default=""),
    "device_coordinate_name": StringProperty(name="Coordinate Name", default="Coordinate"),
    "device_coordinate_id": StringProperty(name="Coordinate ID", default=""),
    "device_coordinate_kind": EnumProperty(name="Coordinate Kind", items=_COORDINATE_KIND_ITEMS, default=CoordinateKind.ROTATION.value),
    "device_coordinate_axis_x": FloatProperty(name="Axis X", default=1.0),
    "device_coordinate_axis_y": FloatProperty(name="Axis Y", default=0.0),
    "device_coordinate_axis_z": FloatProperty(name="Axis Z", default=0.0),
    "new_device_sensor_name": StringProperty(name="Sensor Name", default="Sensor"),
    "new_device_sensor_id": StringProperty(name="Sensor ID", default=""),
    "device_sensor_kind": EnumProperty(name="Sensor Kind", items=_SENSOR_KIND_ITEMS, default=SensorKind.POSITION.value),
    "device_sensor_frame_id": StringProperty(name="Sensor Site ID", default=""),
    "device_sensor_link_id": StringProperty(name="Sensor Link ID", default=""),
    "new_device_actuator_name": StringProperty(name="Actuator Name", default="Actuator"),
    "new_device_actuator_id": StringProperty(name="Actuator ID", default=""),
    "device_actuator_kind": EnumProperty(name="Actuator Kind", items=_ACTUATOR_KIND_ITEMS, default=ActuatorKind.MOTOR.value),
    "device_actuator_joint_id": StringProperty(name="Actuator Joint ID", default=""),
    "device_actuator_coordinate_id": StringProperty(name="Actuator Coordinate ID", default=""),
    "muscle_id": StringProperty(name="Muscle ID", default=""),
    "muscle_name": StringProperty(name="Muscle Name", default="Muscle"),
    "new_path_point_name": StringProperty(name="Point Name", default="Point"),
    "new_path_point_id": StringProperty(name="Point ID", default=""),
    "path_point_kind": EnumProperty(name="Point Kind", items=_MUSCLE_PATH_POINT_KIND_ITEMS, default=MusclePathPointKind.VIA.value),
    "path_point_link_id": StringProperty(name="Link ID", default=""),
    "path_point_site_id": StringProperty(name="Site ID", default=""),
    "path_point_order": FloatProperty(name="Order", default=0.0),
    "new_wrap_name": StringProperty(name="Wrap Name", default="Wrap"),
    "new_wrap_id": StringProperty(name="Wrap ID", default=""),
    "wrap_kind": EnumProperty(name="Wrap Kind", items=_WRAP_GEOMETRY_KIND_ITEMS, default=WrapGeometryKind.CYLINDER.value),
    "wrap_link_id": StringProperty(name="Wrap Link ID", default=""),
    "wrap_site_id": StringProperty(name="Wrap Site ID", default=""),
    "wrap_radius": FloatProperty(name="Radius", default=0.01, min=0.0),
    "wrap_height": FloatProperty(name="Height", default=0.05, min=0.0),
    "assembly_id": StringProperty(name="Assembly ID", default="assembly"),
    "assembly_name": StringProperty(name="Assembly Name", default="assembly"),
    "new_attachment_name": StringProperty(name="Attachment Name", default="Attachment"),
    "new_attachment_id": StringProperty(name="Attachment ID", default=""),
    "attachment_device_id": StringProperty(name="Device ID", default=""),
    "attachment_interface_id": StringProperty(name="Interface ID", default=""),
    "attachment_anatomical_site_id": StringProperty(name="Anatomical Site ID", default=""),
    "new_landmark_name": StringProperty(name="Landmark Name", default="Landmark"),
    "new_landmark_id": StringProperty(name="Landmark ID", default=""),
    "landmark_body_id": StringProperty(name="Link ID", default=""),
    "landmark_frame_id": StringProperty(name="Site ID", default=""),
}


CLASSES = (MELOSAddonSettings,)

__all__ = ["CLASSES", "MELOSAddonSettings"]

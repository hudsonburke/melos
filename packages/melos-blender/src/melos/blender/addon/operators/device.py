from __future__ import annotations

import importlib
from typing import Any, cast

from melos.core.kinematics.enums import CoordinateKind, JointKind
from melos.core.system.enums import ActuatorKind, SensorKind

from melos.blender.constants import (
    DEVICE_ACTUATOR_COORDINATE_ID_KEY,
    DEVICE_ACTUATOR_KIND_KEY,
    DEVICE_ACTUATOR_JOINT_ID_KEY,
    DEVICE_ACTUATOR_KIND,
    DEVICE_FRAME_KIND,
    DEVICE_FRAME_LINK_ID_KEY,
    DEVICE_JOINT_CHILD_FRAME_ID_KEY,
    DEVICE_JOINT_CHILD_LINK_ID_KEY,
    DEVICE_JOINT_KIND,
    DEVICE_JOINT_KIND_KEY,
    DEVICE_JOINT_PARENT_FRAME_ID_KEY,
    DEVICE_JOINT_PARENT_LINK_ID_KEY,
    DEVICE_LINK_ID_KEY,
    DEVICE_LINK_KIND,
    DEVICE_SENSOR_FRAME_ID_KEY,
    DEVICE_SENSOR_KIND,
    DEVICE_SENSOR_KIND_KEY,
    DEVICE_SENSOR_LINK_ID_KEY,
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    JOINT_COORDINATE_AXIS_KEY,
    JOINT_COORDINATE_ID_KEY,
    JOINT_COORDINATE_KIND_KEY,
    JOINT_COORDINATE_NAME_KEY,
    SCENE_SETTINGS_ATTRIBUTE,
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


class MELOS_OT_create_device_link(OperatorBase):
    bl_idname = "melos.create_device_link"
    bl_label = "Create Device Link"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        link_ids = _existing_entity_ids(context.scene, DEVICE_LINK_KIND)
        base_name = settings.new_device_link_name or "Link"
        link_id = settings.new_device_link_id or allocate_identifier(base_name, link_ids, fallback="link")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_LINK_KIND
        object_[ENTITY_ID_KEY] = link_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_LINK_ID_KEY] = link_id
        if not settings.device_root_link_id:
            settings.device_root_link_id = link_id
        _report(self, {"INFO"}, f"Created device link {link_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_device_frame(OperatorBase):
    bl_idname = "melos.create_device_frame"
    bl_label = "Create Device Frame"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        frame_ids = _existing_entity_ids(context.scene, DEVICE_FRAME_KIND)
        base_name = settings.new_device_frame_name or "Frame"
        frame_id = settings.new_device_frame_id or allocate_identifier(base_name, frame_ids, fallback="frame")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_FRAME_KIND
        object_[ENTITY_ID_KEY] = frame_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_FRAME_LINK_ID_KEY] = settings.device_frame_link_id or ""
        _report(self, {"INFO"}, f"Created device frame {frame_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_device_joint(OperatorBase):
    bl_idname = "melos.create_device_joint"
    bl_label = "Create Device Joint"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        joint_ids = _existing_entity_ids(context.scene, DEVICE_JOINT_KIND)
        base_name = settings.new_device_joint_name or "Joint"
        joint_id = settings.new_device_joint_id or allocate_identifier(base_name, joint_ids, fallback="joint")
        coordinate_id = settings.device_coordinate_id or allocate_identifier(
            settings.device_coordinate_name or f"{base_name} Coordinate",
            _existing_device_coordinate_ids(context.scene),
            fallback="coordinate",
        )
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_JOINT_KIND
        object_[ENTITY_ID_KEY] = joint_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_JOINT_KIND_KEY] = settings.device_joint_kind or JointKind.REVOLUTE.value
        object_[DEVICE_JOINT_PARENT_LINK_ID_KEY] = settings.device_joint_parent_link_id or ""
        object_[DEVICE_JOINT_CHILD_LINK_ID_KEY] = settings.device_joint_child_link_id or ""
        object_[DEVICE_JOINT_PARENT_FRAME_ID_KEY] = settings.device_joint_parent_frame_id or ""
        object_[DEVICE_JOINT_CHILD_FRAME_ID_KEY] = settings.device_joint_child_frame_id or ""
        object_[JOINT_COORDINATE_ID_KEY] = coordinate_id
        object_[JOINT_COORDINATE_NAME_KEY] = settings.device_coordinate_name or coordinate_id
        object_[JOINT_COORDINATE_KIND_KEY] = settings.device_coordinate_kind or CoordinateKind.ROTATION.value
        object_[JOINT_COORDINATE_AXIS_KEY] = (
            settings.device_coordinate_axis_x,
            settings.device_coordinate_axis_y,
            settings.device_coordinate_axis_z,
        )
        _report(self, {"INFO"}, f"Created device joint {joint_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_device_sensor(OperatorBase):
    bl_idname = "melos.create_device_sensor"
    bl_label = "Create Device Sensor"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        sensor_ids = _existing_entity_ids(context.scene, DEVICE_SENSOR_KIND)
        base_name = settings.new_device_sensor_name or "Sensor"
        sensor_id = settings.new_device_sensor_id or allocate_identifier(base_name, sensor_ids, fallback="sensor")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_SENSOR_KIND
        object_[ENTITY_ID_KEY] = sensor_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_SENSOR_KIND_KEY] = settings.device_sensor_kind or SensorKind.POSITION.value
        object_[DEVICE_SENSOR_FRAME_ID_KEY] = settings.device_sensor_frame_id or ""
        object_[DEVICE_SENSOR_LINK_ID_KEY] = settings.device_sensor_link_id or ""
        _report(self, {"INFO"}, f"Created device sensor {sensor_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_device_actuator(OperatorBase):
    bl_idname = "melos.create_device_actuator"
    bl_label = "Create Device Actuator"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        actuator_ids = _existing_entity_ids(context.scene, DEVICE_ACTUATOR_KIND)
        base_name = settings.new_device_actuator_name or "Actuator"
        actuator_id = settings.new_device_actuator_id or allocate_identifier(base_name, actuator_ids, fallback="actuator")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_ACTUATOR_KIND
        object_[ENTITY_ID_KEY] = actuator_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_ACTUATOR_KIND_KEY] = settings.device_actuator_kind or ActuatorKind.MOTOR.value
        object_[DEVICE_ACTUATOR_JOINT_ID_KEY] = settings.device_actuator_joint_id or ""
        object_[DEVICE_ACTUATOR_COORDINATE_ID_KEY] = settings.device_actuator_coordinate_id or ""
        _report(self, {"INFO"}, f"Created device actuator {actuator_id!r}.")
        return {"FINISHED"}


def _create_empty(context, *, name: str):
    if bpy is None:
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


def _existing_device_coordinate_ids(scene) -> set[str]:
    return {
        str(object_.get(JOINT_COORDINATE_ID_KEY))
        for object_ in scene.objects
        if object_.get(ENTITY_KIND_KEY) == DEVICE_JOINT_KIND
        and object_.get(JOINT_COORDINATE_ID_KEY)
    }


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (
    MELOS_OT_create_device_link,
    MELOS_OT_create_device_frame,
    MELOS_OT_create_device_joint,
    MELOS_OT_create_device_sensor,
    MELOS_OT_create_device_actuator,
)

__all__ = [
    "CLASSES",
    "MELOS_OT_create_device_actuator",
    "MELOS_OT_create_device_frame",
    "MELOS_OT_create_device_joint",
    "MELOS_OT_create_device_link",
    "MELOS_OT_create_device_sensor",
]

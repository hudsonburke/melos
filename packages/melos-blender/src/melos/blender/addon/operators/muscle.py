from __future__ import annotations

import importlib
from typing import Any, cast

from melos.core.actuator.muscles.enums import MusclePathPointKind, WrapGeometryKind

from melos.blender.constants import (
    ENTITY_KIND_KEY,
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    MUSCLE_ID_KEY,
    MUSCLE_NAME_KEY,
    MUSCLE_PATH_POINT_LINK_ID_KEY,
    MUSCLE_PATH_POINT_SITE_ID_KEY,
    MUSCLE_PATH_POINT_KIND,
    MUSCLE_PATH_POINT_KIND_KEY,
    MUSCLE_PATH_POINT_ORDER_KEY,
    MUSCLE_WRAP_LINK_ID_KEY,
    MUSCLE_WRAP_SITE_ID_KEY,
    MUSCLE_WRAP_GEOMETRY_KIND,
    MUSCLE_WRAP_HEIGHT_KEY,
    MUSCLE_WRAP_KIND_KEY,
    MUSCLE_WRAP_RADIUS_KEY,
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


class MELOS_OT_create_muscle_path_point(OperatorBase):

    bl_idname = "melos.create_muscle_path_point"
    bl_label = "Create Muscle Path Point"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        point_ids = _existing_entity_ids(context.scene, MUSCLE_PATH_POINT_KIND)
        base_name = settings.new_path_point_name or "Point"
        point_id = settings.new_path_point_id or allocate_identifier(base_name, point_ids, fallback="point")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = MUSCLE_PATH_POINT_KIND
        object_[ENTITY_ID_KEY] = point_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[MUSCLE_ID_KEY] = settings.muscle_id or ""
        object_[MUSCLE_PATH_POINT_KIND_KEY] = settings.path_point_kind or MusclePathPointKind.VIA.value
        object_[MUSCLE_PATH_POINT_LINK_ID_KEY] = settings.path_point_link_id or ""
        object_[MUSCLE_PATH_POINT_SITE_ID_KEY] = settings.path_point_site_id or ""
        object_[MUSCLE_PATH_POINT_ORDER_KEY] = float(settings.path_point_order)
        _report(self, {"INFO"}, f"Created muscle path point {point_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_wrap_geometry(OperatorBase):

    bl_idname = "melos.create_wrap_geometry"
    bl_label = "Create Wrap Geometry"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        wrap_ids = _existing_entity_ids(context.scene, MUSCLE_WRAP_GEOMETRY_KIND)
        base_name = settings.new_wrap_name or "Wrap"
        wrap_id = settings.new_wrap_id or allocate_identifier(base_name, wrap_ids, fallback="wrap")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = MUSCLE_WRAP_GEOMETRY_KIND
        object_[ENTITY_ID_KEY] = wrap_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[MUSCLE_ID_KEY] = settings.muscle_id or ""
        object_[MUSCLE_WRAP_KIND_KEY] = settings.wrap_kind or WrapGeometryKind.CYLINDER.value
        object_[MUSCLE_WRAP_LINK_ID_KEY] = settings.wrap_link_id or ""
        object_[MUSCLE_WRAP_SITE_ID_KEY] = settings.wrap_site_id or ""
        object_[MUSCLE_WRAP_RADIUS_KEY] = float(settings.wrap_radius)
        object_[MUSCLE_WRAP_HEIGHT_KEY] = float(settings.wrap_height)
        _report(self, {"INFO"}, f"Created wrap geometry {wrap_id!r}.")
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


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (
    MELOS_OT_create_muscle_path_point,
    MELOS_OT_create_wrap_geometry,
)

__all__ = [
    "CLASSES",
    "MELOS_OT_create_muscle_path_point",
    "MELOS_OT_create_wrap_geometry",
]

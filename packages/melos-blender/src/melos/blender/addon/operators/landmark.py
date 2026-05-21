from __future__ import annotations

import importlib
from typing import Any, cast

from melos.blender.constants import (
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    LANDMARK_BODY_ID_KEY,
    LANDMARK_FRAME_ID_KEY,
    LANDMARK_KIND,
    SCENE_SETTINGS_ATTRIBUTE,
    ANATOMICAL_LINK_KIND,
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


class MELOS_OT_create_landmark(OperatorBase):
    bl_idname = "melos.create_landmark"
    bl_label = "Create Landmark"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        landmark_ids = _existing_entity_ids(context.scene, LANDMARK_KIND)
        base_name = settings.new_landmark_name or "Landmark"
        landmark_id = settings.new_landmark_id or allocate_identifier(base_name, landmark_ids, fallback="landmark")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = LANDMARK_KIND
        object_[ENTITY_ID_KEY] = landmark_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[LANDMARK_BODY_ID_KEY] = settings.landmark_body_id or _selected_body_id(context)
        object_[LANDMARK_FRAME_ID_KEY] = settings.landmark_frame_id or ""

        parent_body = _selected_body_object(context)
        if parent_body is not None:
            object_.parent = parent_body
            object_.matrix_parent_inverse = parent_body.matrix_world.inverted()

        _report(self, {"INFO"}, f"Created landmark {landmark_id!r}.")
        return {"FINISHED"}


def _create_empty(context, *, name: str):
    if bpy is None:  # pragma: no cover - Blender-only path
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


def _selected_body_object(context):
    object_ = getattr(context, "active_object", None)
    if object_ is None:
        return None
    if object_.get(ENTITY_KIND_KEY) != ANATOMICAL_LINK_KIND:
        return None
    return object_


def _selected_body_id(context) -> str:
    object_ = _selected_body_object(context)
    if object_ is None:
        return ""
    return str(object_.get(ENTITY_ID_KEY, ""))


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (MELOS_OT_create_landmark,)

__all__ = [
    "CLASSES",
    "MELOS_OT_create_landmark",
]

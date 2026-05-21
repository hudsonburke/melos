from __future__ import annotations

import importlib
from typing import Any, cast

from melos.blender.constants import (
    ATTACHMENT_DEVICE_ID_KEY,
    ATTACHMENT_INTERFACE_ID_KEY,
    ATTACHMENT_KIND,
    ATTACHMENT_ANATOMICAL_SITE_ID_KEY,
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
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


class MELOS_OT_create_attachment(OperatorBase):
    bl_idname = "melos.create_attachment"
    bl_label = "Create Attachment"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        attachment_ids = _existing_entity_ids(context.scene, ATTACHMENT_KIND)
        base_name = settings.new_attachment_name or "Attachment"
        attachment_id = settings.new_attachment_id or allocate_identifier(
            base_name, attachment_ids, fallback="attachment"
        )
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = ATTACHMENT_KIND
        object_[ENTITY_ID_KEY] = attachment_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[ATTACHMENT_DEVICE_ID_KEY] = settings.attachment_device_id or ""
        object_[ATTACHMENT_INTERFACE_ID_KEY] = settings.attachment_interface_id or ""
        object_[ATTACHMENT_ANATOMICAL_SITE_ID_KEY] = settings.attachment_anatomical_site_id or ""
        _report(self, {"INFO"}, f"Created attachment {attachment_id!r}.")
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


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (MELOS_OT_create_attachment,)

__all__ = [
    "CLASSES",
    "MELOS_OT_create_attachment",
]

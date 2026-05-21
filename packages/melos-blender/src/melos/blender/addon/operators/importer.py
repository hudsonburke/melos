from __future__ import annotations

import importlib
from typing import Any, cast

from melos.core.io.json import load_project

from melos.blender.bpy_io.importer import import_project_to_scene
from melos.blender.constants import SCENE_SETTINGS_ATTRIBUTE


try:
    bpy = importlib.import_module("bpy")
except ModuleNotFoundError:
    bpy = None


if bpy is not None:
    StringProperty = bpy.props.StringProperty
    OperatorBase = bpy.types.Operator
else:
    StringProperty = None

    class OperatorBase:
        pass


class MELOS_OT_import_project(OperatorBase):

    bl_idname = "melos.import_project"
    bl_label = "Import Project"

    if StringProperty is not None:
        filepath: StringProperty(subtype="FILE_PATH")  # type: ignore[valid-type]

    def execute(self, context):
        try:
            filepath = getattr(self, "filepath", "")
            project = load_project(filepath)
            scene = context.scene
            settings = getattr(scene, SCENE_SETTINGS_ATTRIBUTE)
            created = import_project_to_scene(project, scene, settings)
            _report(self, {"INFO"}, f"Imported {len(created)} objects from {filepath!r}.")
            return {"FINISHED"}
        except Exception as exc:  # pragma: no cover - Blender-facing path
            _report(self, {"ERROR"}, str(exc))
            return {"CANCELLED"}


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (MELOS_OT_import_project,)

__all__ = ["CLASSES", "MELOS_OT_import_project"]

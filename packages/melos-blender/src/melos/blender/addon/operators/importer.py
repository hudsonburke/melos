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

try:
    from bpy_extras.io_utils import ImportHelper
except (ImportError, ModuleNotFoundError):
    ImportHelper = object  # fallback for headless mode

if bpy is not None:
    StringProperty = bpy.props.StringProperty
    OperatorBase = bpy.types.Operator
else:
    StringProperty = None

    class OperatorBase:
        pass


class MELOS_OT_import_project(OperatorBase, ImportHelper):

    bl_idname = "melos.import_project"
    bl_label = "Import Melos Project"
    bl_options = {"REGISTER", "UNDO"}

    if StringProperty is not None:
        filter_glob: StringProperty(
            default="*.json",
            options={"HIDDEN"},
        )  # type: ignore[valid-type]

    def execute(self, context):
        try:
            filepath = getattr(self, "filepath", "")
            project = load_project(filepath)
            scene = context.scene
            settings = getattr(scene, SCENE_SETTINGS_ATTRIBUTE)
            created = import_project_to_scene(project, scene, settings)
            _report(self, {"INFO"}, f"Imported {len(created)} objects from {filepath!r}.")
            return {"FINISHED"}
        except Exception as exc:
            _report(self, {"ERROR"}, str(exc))
            return {"CANCELLED"}


class MELOS_OT_import_mjcf(OperatorBase, ImportHelper):

    bl_idname = "melos.import_mjcf"
    bl_label = "Import MuJoCo Model"
    bl_options = {"REGISTER", "UNDO"}

    if StringProperty is not None:
        filter_glob: StringProperty(
            default="*.xml",
            options={"HIDDEN"},
        )  # type: ignore[valid-type]

    def execute(self, context):
        try:
            filepath = getattr(self, "filepath", "")
            from melos.sim import import_mjcf
            result = import_mjcf(filepath)
            project = result.project
            from melos.blender.services.example_workflow import display_project_in_scene
            _, _, body_meshes = display_project_in_scene(project, context)
            warning_count = len(result.report.warnings) if hasattr(result, "report") else 0
            msg = f"Imported model from {filepath!r} ({len(body_meshes)} body meshes)"
            if warning_count:
                msg += f" ({warning_count} warnings)"
            _report(self, {"INFO"}, msg)
            return {"FINISHED"}
        except Exception as exc:
            _report(self, {"ERROR"}, str(exc))
            return {"CANCELLED"}


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (MELOS_OT_import_project, MELOS_OT_import_mjcf)

__all__ = ["CLASSES", "MELOS_OT_import_project", "MELOS_OT_import_mjcf"]

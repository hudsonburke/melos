"""Joint FK operators for the melos Blender add-on."""

from __future__ import annotations

import importlib
import json
from typing import Any, cast

try:
    bpy = importlib.import_module("bpy")
except ModuleNotFoundError:
    bpy = None

if bpy is not None:
    OperatorBase = bpy.types.Operator
else:
    class OperatorBase:
        pass


def _find_fk_armature(context: Any) -> Any | None:
    """Find an armature with FK metadata, preferring the active object."""
    obj = getattr(context, "active_object", None)
    if obj is not None and hasattr(obj, "get") and obj.get("melos_fk_system"):
        return obj
    scene = getattr(context, "scene", None)
    if scene is None:
        return None
    for obj in getattr(scene, "objects", []):
        if hasattr(obj, "get") and obj.get("melos_fk_system"):
            return obj
    return None


class MELOS_OT_reset_fk(OperatorBase):
    """Reset all joint coordinates to their default values."""

    bl_idname = "melos.reset_fk"
    bl_label = "Reset FK"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: Any) -> set[str]:
        arm_obj = _find_fk_armature(context)
        if arm_obj is None:
            _report(self, {"ERROR"}, "No FK-enabled armature found.")
            return {"CANCELLED"}

        raw = arm_obj.get("melos_fk_system", "{}")
        try:
            fk_data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            _report(self, {"ERROR"}, "Invalid FK metadata on armature.")
            return {"CANCELLED"}

        reset = 0
        for coord_entry in fk_data.get("coordinates", []):
            prop_name = f'melos_fk_{coord_entry["id"]}'
            default = coord_entry.get("default_value", 0.0)
            if hasattr(arm_obj, "__setitem__"):
                arm_obj[prop_name] = default
            reset += 1

        # Force viewport update — Blender drivers will re-compute bone rotations
        view_layer = getattr(context, "view_layer", None)
        if view_layer is not None and hasattr(view_layer, "update"):
            view_layer.update()

        _report(self, {"INFO"}, f"Reset {reset} coordinates to defaults.")
        return {"FINISHED"}


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (MELOS_OT_reset_fk,)

__all__ = ["CLASSES", "MELOS_OT_reset_fk", "_find_fk_armature"]

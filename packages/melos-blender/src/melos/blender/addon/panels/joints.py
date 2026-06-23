"""Joint FK controls panel for the melos Blender add-on."""

from __future__ import annotations

import importlib
import json
from typing import Any, cast

from melos.blender.constants import ADDON_NAME

from melos.blender.addon.operators.joints import _find_fk_armature


try:
    bpy = importlib.import_module("bpy")
except ModuleNotFoundError:
    bpy = None


if bpy is not None:
    PanelBase = bpy.types.Panel
else:
    class PanelBase:
        pass


class MELOS_PT_joints(PanelBase):
    """Joint coordinate controls for forward kinematics."""

    bl_label = "Joint Controls"
    bl_idname = "MELOS_PT_joints"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME

    @classmethod
    def poll(cls, context: Any) -> bool:
        return _find_fk_armature(context) is not None

    def draw(self, context: Any) -> None:
        layout = cast(Any, self).layout
        arm_obj = _find_fk_armature(context)
        if arm_obj is None:
            layout.label(text="No FK-enabled armature found.")
            return

        raw = arm_obj.get("melos_fk_system", "{}")
        try:
            fk_data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            layout.label(text="Invalid FK metadata.")
            return

        # Group coordinates by joint
        coord_by_joint: dict[str, list[dict]] = {}
        for coord in fk_data.get("coordinates", []):
            coord_by_joint.setdefault(coord["joint_id"], []).append(coord)

        for joint_id, coords in coord_by_joint.items():
            box = layout.box()
            box.label(text=joint_id)
            for coord in coords:
                prop_name = f'melos_fk_{coord["id"]}'
                box.prop(arm_obj, f'["{prop_name}"]', text=coord["id"])

        layout.separator()
        layout.operator("melos.reset_fk")
        layout.label(text="Adjust sliders to pose (live update)", icon="INFO")


CLASSES = (MELOS_PT_joints,)

__all__ = ["CLASSES", "MELOS_PT_joints"]

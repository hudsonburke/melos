"""Visualization panels for the melos Blender add-on.

Provides scene setup, color configuration, muscle display controls,
and MuJoCo model loading panels — inspired by MuSkeMo's visualization
workflow but tailored for subject-specific exoskeleton design.
"""

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


class MELOS_PT_visualization(PanelBase):
    """Top-level visualization panel for MuJoCo model display."""

    bl_label = "Visualization"
    bl_idname = "MELOS_PT_visualization"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: Any) -> None:
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        layout.label(text="MuJoCo model visualization and scene setup.")
        layout.separator()




class MELOS_PT_visualization_colors(PanelBase):
    """Color configuration subpanel for model elements."""

    bl_label = "Colors"
    bl_idname = "MELOS_PT_visualization_colors"
    bl_parent_id = "MELOS_PT_visualization"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: Any) -> None:
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)

        box = layout.box()
        box.label(text="Element Colors", icon="COLOR")
        box.prop(settings, "viz_bone_color", text="Bones")
        box.prop(settings, "viz_muscle_color", text="Muscles")
        box.prop(settings, "viz_joint_color", text="Joints")
        box.prop(settings, "viz_device_color", text="Device")
        box.prop(settings, "viz_cable_color", text="Cables")

        layout.separator()
        layout.operator("melos.apply_visualization_colors", text="Apply Colors")


class MELOS_PT_visualization_muscles(PanelBase):
    """Muscle display subpanel."""

    bl_label = "Muscle Display"
    bl_idname = "MELOS_PT_visualization_muscles"
    bl_parent_id = "MELOS_PT_visualization"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: Any) -> None:
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)

        layout.prop(settings, "viz_muscle_display_mode", text="Mode")
        layout.prop(settings, "viz_muscle_radius")
        layout.separator()
        row = layout.row(align=True)
        row.operator("melos.show_muscle_tubes", text="Show Tubes")
        row.operator("melos.hide_muscles", text="Hide")


class MELOS_PT_visualization_visibility(PanelBase):
    """Visibility toggles for MuJoCo model elements."""

    bl_label = "Visibility"
    bl_idname = "MELOS_PT_visualization_visibility"
    bl_parent_id = "MELOS_PT_visualization"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: Any) -> None:
        layout = cast(Any, self).layout
        row = layout.row(align=True)
        row.operator("melos.toggle_sites_visibility", text="Toggle Sites")
        row.operator("melos.toggle_geoms_visibility", text="Toggle Geoms")


CLASSES = (
    MELOS_PT_visualization,
    MELOS_PT_visualization_colors,
    MELOS_PT_visualization_muscles,
    MELOS_PT_visualization_visibility,
)

__all__ = ["CLASSES"]

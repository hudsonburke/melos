"""Project and simulation panels for the melos Blender add-on."""

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


class MELOS_PT_project(PanelBase):
    """Scene-level project and export controls."""

    bl_label = "Project"
    bl_idname = "MELOS_PT_project"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_NAME

    def draw(self, context):
        layout = cast(Any, self).layout
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        layout.prop(settings, "project_id")
        layout.prop(settings, "project_name")
        layout.prop(settings, "project_description")
        layout.prop(settings, "created_by")
        layout.separator()
        layout.prop(settings, "time_step")
        layout.prop(settings, "duration")
        row = layout.row(align=True)
        row.prop(settings, "gravity_x")
        row.prop(settings, "gravity_y")
        row.prop(settings, "gravity_z")
        layout.separator()
        layout.prop(settings, "export_path")
        layout.operator("melos.validate_project")
        layout.operator("melos.export_project_json")
        layout.operator("melos.create_example_project")
        layout.operator("melos.create_example_model_project")
        layout.operator("melos.analyze_example_scale")

        project_ops = importlib.import_module("melos.blender.addon.operators.project")
        body_reference_objects = project_ops._example_body_mesh_reference_objects(context.scene)
        if body_reference_objects:
            any_visible = project_ops._example_body_mesh_references_visible(context.scene)
            visible_count = sum(
                1 for obj in body_reference_objects if not getattr(obj, "hide_viewport", False)
            )
            layout.separator()
            layout.label(text=f"MuJoCo body refs: {visible_count}/{len(body_reference_objects)} visible")
            layout.operator(
                "melos.toggle_example_body_mesh_references",
                text=(
                    "Hide MuJoCo Body Mesh References"
                    if any_visible
                    else "Show MuJoCo Body Mesh References"
                ),
            )


CLASSES = (MELOS_PT_project,)

__all__ = ["CLASSES", "MELOS_PT_project"]

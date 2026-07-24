"""Visualization operators for the melos Blender add-on.

Provides scene setup, color management, muscle display modes, and
visibility toggles for subject-specific exoskeleton design visualization.
Model loading is handled by the existing melos.import_mjcf importer.
"""

from __future__ import annotations

import importlib
import math
from typing import Any, cast

from melos.blender.constants import SCENE_SETTINGS_ATTRIBUTE

try:
    bpy = importlib.import_module("bpy")
except ModuleNotFoundError:
    bpy = None


if bpy is not None:
    OperatorBase = bpy.types.Operator
else:
    class OperatorBase:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_settings(context: Any) -> Any:
    return getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


def _ensure_collection(name: str) -> Any:
    """Get or create a Blender collection by name."""
    if bpy is None:
        return None
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def _create_or_update_material(name: str, rgba: tuple[float, ...]) -> Any:
    """Get or create a material with the given RGBA color."""
    if bpy is None:
        return None
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
    if mat.use_nodes:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = rgba[:4]
    return mat


# ---------------------------------------------------------------------------
# Scene Setup
# ---------------------------------------------------------------------------

class MELOS_OT_create_ground_plane(OperatorBase):
    """Create a ground plane with a 1 m grid for model visualization."""

    bl_idname = "melos.create_ground_plane"
    bl_label = "Create Ground Plane"
    bl_description = "Create a ground plane with 1 m grid lines for visualization"
    bl_options = {"UNDO"}

    def execute(self, context: Any) -> set[str]:
        if bpy is None:
            return {"CANCELLED"}

        existing = bpy.data.objects.get("Ground Plane")
        if existing is not None:
            bpy.data.objects.remove(existing, do_unlink=True)

        bpy.ops.mesh.primitive_plane_add(
            size=100,
            enter_editmode=False,
            align="WORLD",
            location=(0, 0, 0),
            rotation=(-math.pi / 2, 0, 0),
            scale=(1, 1, 1),
        )
        plane = context.active_object
        plane.name = "Ground Plane"

        mat = bpy.data.materials.new(name="Ground Plane Mat")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        tex_node = nodes.new("ShaderNodeTexBrick")
        tex_node.offset = 0
        tex_node.squash = 0.5
        tex_node.squash_frequency = 1
        tex_node.inputs["Color1"].default_value = (0.85, 0.85, 0.85, 1)
        tex_node.inputs["Color2"].default_value = (0.85, 0.85, 0.85, 1)
        tex_node.inputs["Mortar"].default_value = (0.28, 0.002, 0.022, 1)
        tex_node.inputs["Scale"].default_value = 25
        tex_node.inputs["Mortar Size"].default_value = 0.0025

        bsdf_node = nodes.get("Principled BSDF")
        if bsdf_node is not None:
            links.new(tex_node.outputs["Color"], bsdf_node.inputs["Base Color"])

        plane.data.materials.append(mat)
        plane.lock_location = (True, True, True)
        plane.lock_rotation = (True, True, True)

        _report(self, {"INFO"}, "Created ground plane with 1 m grid")
        return {"FINISHED"}


class MELOS_OT_set_background_gradient(OperatorBase):
    """Set up a compositor background gradient for renders."""

    bl_idname = "melos.set_background_gradient"
    bl_label = "Set Background Gradient"
    bl_description = "Add compositor nodes for a distance-based background gradient"
    bl_options = {"UNDO"}

    def execute(self, context: Any) -> set[str]:
        if bpy is None:
            return {"CANCELLED"}

        scene = context.scene
        scene.view_layers["ViewLayer"].use_pass_mist = True
        scene.use_nodes = True

        nodes = scene.node_tree.nodes
        links = scene.node_tree.links

        render_layers = nodes.get("Render Layers")
        composite = nodes.get("Composite")

        inv_node = nodes.new("CompositorNodeInvert")
        inv_node.location = (0, 500)

        mix_node = nodes.new("CompositorNodeMixRGB")
        mix_node.blend_type = "MULTIPLY"
        mix_node.location = (300, -200)

        viewer_node = nodes.new("CompositorNodeViewer")
        viewer_node.location = (500, -700)

        if render_layers is not None:
            links.new(inv_node.inputs["Color"], render_layers.outputs["Mist"])
            links.new(mix_node.inputs[1], render_layers.outputs["Image"])

        links.new(mix_node.inputs[2], inv_node.outputs["Color"])

        if composite is not None:
            links.new(composite.inputs["Image"], mix_node.outputs["Image"])
            links.new(viewer_node.inputs["Image"], mix_node.outputs["Image"])

        _report(self, {"INFO"}, "Set background gradient via compositor")
        return {"FINISHED"}


class MELOS_OT_setup_visualization_scene(OperatorBase):
    """One-click scene setup: ground plane + gradient + camera + lighting."""

    bl_idname = "melos.setup_visualization_scene"
    bl_label = "Setup Visualization Scene"
    bl_description = "Set up ground plane, background gradient, camera, and lighting for model visualization"
    bl_options = {"UNDO"}

    def execute(self, context: Any) -> set[str]:
        if bpy is None:
            return {"CANCELLED"}

        bpy.ops.melos.create_ground_plane()
        bpy.ops.melos.set_background_gradient()

        cam = bpy.data.objects.get("Camera")
        if cam is None:
            cam_data = bpy.data.cameras.new(name="Camera")
            cam = bpy.data.objects.new("Camera", cam_data)
            context.scene.collection.objects.link(cam)
        cam.location = (2.0, -2.0, 1.5)
        cam.rotation_euler = (math.radians(65), 0, math.radians(45))
        cam.data.lens = 50
        context.scene.camera = cam

        sun = bpy.data.objects.get("Sun")
        if sun is None:
            sun_data = bpy.data.lights.new(name="Sun", type="SUN")
            sun = bpy.data.objects.new("Sun", sun_data)
            context.scene.collection.objects.link(sun)
        sun.location = (2.0, -1.0, 4.0)
        sun.rotation_euler = (math.radians(45), 0, math.radians(30))
        sun.data.energy = 3.0

        fill = bpy.data.objects.get("Fill Light")
        if fill is None:
            fill_data = bpy.data.lights.new(name="Fill Light", type="AREA")
            fill = bpy.data.objects.new("Fill Light", fill_data)
            context.scene.collection.objects.link(fill)
        fill.location = (-2.0, -1.5, 2.0)
        fill.data.energy = 100.0
        fill.data.size = 3.0

        scene = context.scene
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080

        _report(self, {"INFO"}, "Visualization scene configured")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Color Management
# ---------------------------------------------------------------------------

class MELOS_OT_apply_visualization_colors(OperatorBase):
    """Apply configured colors to model elements based on entity type."""

    bl_idname = "melos.apply_visualization_colors"
    bl_label = "Apply Visualization Colors"
    bl_description = "Apply configured colors to bones, muscles, joints, and device elements"
    bl_options = {"UNDO"}

    def execute(self, context: Any) -> set[str]:
        if bpy is None:
            return {"CANCELLED"}

        settings = _get_settings(context)

        _create_or_update_material("melos_bone", (*settings.viz_bone_color, 1.0))
        _create_or_update_material("melos_muscle", (*settings.viz_muscle_color, 1.0))
        _create_or_update_material("melos_joint", (*settings.viz_joint_color, 1.0))
        _create_or_update_material("melos_device", (*settings.viz_device_color, 1.0))
        _create_or_update_material("melos_cable", (*settings.viz_cable_color, 1.0))

        applied = 0
        for obj in context.scene.objects:
            entity_kind = obj.get("melos_entity_kind", "")
            mat_name = None

            if entity_kind in ("anatomical_link", "anatomical_link_asset"):
                mat_name = "melos_bone"
            elif entity_kind == "muscle_path_point":
                mat_name = "melos_muscle"
            elif entity_kind in ("anatomical_joint", "anatomical_site"):
                mat_name = "melos_joint"
            elif entity_kind in (
                "device_link", "device_frame", "device_joint",
                "device_sensor", "device_actuator", "device_interface",
            ):
                mat_name = "melos_device"
            elif entity_kind == "device_cable_route_point":
                mat_name = "melos_cable"

            if mat_name is not None and obj.type == "MESH":
                mat = bpy.data.materials.get(mat_name)
                if mat is not None:
                    if obj.data.materials:
                        obj.data.materials[0] = mat
                    else:
                        obj.data.materials.append(mat)
                    applied += 1

        _report(self, {"INFO"}, f"Applied colors to {applied} objects")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Muscle Display
# ---------------------------------------------------------------------------

class MELOS_OT_show_muscle_tubes(OperatorBase):
    """Display muscles as tube/cylinder representations."""

    bl_idname = "melos.show_muscle_tubes"
    bl_label = "Show Muscle Tubes"
    bl_description = "Display muscles as simple tube geometry for fast viewport performance"
    bl_options = {"UNDO"}

    def execute(self, context: Any) -> set[str]:
        if bpy is None:
            return {"CANCELLED"}

        settings = _get_settings(context)
        radius = settings.viz_muscle_radius
        count = 0

        for obj in context.scene.objects:
            entity_kind = obj.get("melos_entity_kind", "")
            if entity_kind in ("muscle_path_point", "mujoco_tendon"):
                obj.hide_viewport = False
                obj.hide_render = False
                # Update bevel depth on curve objects
                if obj.type == "CURVE" and hasattr(obj.data, "bevel_depth"):
                    is_cable = obj.name.startswith("cable_")
                    obj.data.bevel_depth = radius if not is_cable else max(radius, 0.005)
                count += 1

        settings.viz_muscle_display_mode = "TUBE"
        _report(self, {"INFO"}, f"Showing {count} muscle elements")
        return {"FINISHED"}


class MELOS_OT_hide_muscles(OperatorBase):
    """Hide all muscle visualization objects."""

    bl_idname = "melos.hide_muscles"
    bl_label = "Hide Muscles"
    bl_description = "Hide all muscle visualization objects from the viewport"
    bl_options = {"UNDO"}

    def execute(self, context: Any) -> set[str]:
        if bpy is None:
            return {"CANCELLED"}

        settings = _get_settings(context)
        count = 0

        for obj in context.scene.objects:
            entity_kind = obj.get("melos_entity_kind", "")
            if entity_kind in ("muscle_path_point", "mujoco_tendon"):
                obj.hide_viewport = True
                obj.hide_render = True
                count += 1

        settings.viz_muscle_display_mode = "HIDDEN"
        _report(self, {"INFO"}, f"Hidden {count} muscle elements")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Visibility Helpers
# ---------------------------------------------------------------------------

class MELOS_OT_toggle_sites_visibility(OperatorBase):
    """Toggle visibility of anatomical site objects."""

    bl_idname = "melos.toggle_sites_visibility"
    bl_label = "Toggle Sites"
    bl_description = "Show or hide anatomical site markers in the viewport"
    bl_options = {"UNDO"}

    def execute(self, context: Any) -> set[str]:
        if bpy is None:
            return {"CANCELLED"}

        any_visible = any(
            obj.get("melos_entity_kind") == "anatomical_site" and not obj.hide_viewport
            for obj in context.scene.objects
        )

        new_state = not any_visible
        count = 0
        for obj in context.scene.objects:
            if obj.get("melos_entity_kind") == "anatomical_site":
                obj.hide_viewport = new_state
                obj.hide_render = new_state
                count += 1

        _report(self, {"INFO"}, f"{'hidden' if new_state else 'shown'} {count} site markers")
        return {"FINISHED"}


class MELOS_OT_toggle_geoms_visibility(OperatorBase):
    """Toggle visibility of mesh geometry objects."""

    bl_idname = "melos.toggle_geoms_visibility"
    bl_label = "Toggle Geoms"
    bl_description = "Show or hide mesh geometry in the viewport"
    bl_options = {"UNDO"}

    def execute(self, context: Any) -> set[str]:
        if bpy is None:
            return {"CANCELLED"}

        any_visible = any(
            obj.get("melos_entity_kind") == "anatomical_link_asset" and not obj.hide_viewport
            for obj in context.scene.objects
        )

        new_state = not any_visible
        count = 0
        for obj in context.scene.objects:
            if obj.get("melos_entity_kind") == "anatomical_link_asset":
                obj.hide_viewport = new_state
                obj.hide_render = new_state
                count += 1

        _report(self, {"INFO"}, f"{'hidden' if new_state else 'shown'} {count} mesh objects")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

CLASSES = (
    MELOS_OT_create_ground_plane,
    MELOS_OT_set_background_gradient,
    MELOS_OT_setup_visualization_scene,
    MELOS_OT_apply_visualization_colors,
    MELOS_OT_show_muscle_tubes,
    MELOS_OT_hide_muscles,
    MELOS_OT_toggle_sites_visibility,
    MELOS_OT_toggle_geoms_visibility,
)

__all__ = ["CLASSES"]

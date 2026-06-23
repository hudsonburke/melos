from __future__ import annotations

import importlib
from typing import Any, cast

from melos.core.system.enums import CoordinateKind, JointKind
from melos.core.system.enums import ActuatorKind, RouteNodeKind, SensorKind

from melos.blender.constants import (
    CABLE_ACTUATOR_ID_KEY,
    CABLE_ROUTE_GEOMETRY_ID_KEY,
    CABLE_ROUTE_NODE_KIND_KEY,
    CABLE_ROUTE_ORDER_KEY,
    CABLE_ROUTE_SIDE_SITE_ID_KEY,
    CABLE_ROUTE_SITE_ID_KEY,
    DEVICE_ACTUATOR_COORDINATE_ID_KEY,
    DEVICE_ACTUATOR_KIND,
    DEVICE_ACTUATOR_JOINT_ID_KEY,
    DEVICE_ACTUATOR_KIND_KEY,
    DEVICE_CABLE_ROUTE_POINT_KIND,
    DEVICE_FRAME_KIND,
    DEVICE_FRAME_LINK_ID_KEY,
    DEVICE_JOINT_CHILD_FRAME_ID_KEY,
    DEVICE_JOINT_CHILD_LINK_ID_KEY,
    DEVICE_JOINT_KIND,
    DEVICE_JOINT_KIND_KEY,
    DEVICE_JOINT_PARENT_FRAME_ID_KEY,
    DEVICE_JOINT_PARENT_LINK_ID_KEY,
    DEVICE_LINK_ID_KEY,
    DEVICE_LINK_KIND,
    DEVICE_SENSOR_FRAME_ID_KEY,
    DEVICE_SENSOR_KIND,
    DEVICE_SENSOR_KIND_KEY,
    DEVICE_SENSOR_LINK_ID_KEY,
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    JOINT_COORDINATE_AXIS_KEY,
    JOINT_COORDINATE_ID_KEY,
    JOINT_COORDINATE_KIND_KEY,
    JOINT_COORDINATE_NAME_KEY,
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


class MELOS_OT_create_device_link(OperatorBase):
    bl_idname = "melos.create_device_link"
    bl_label = "Create Device Link"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        link_ids = _existing_entity_ids(context.scene, DEVICE_LINK_KIND)
        base_name = settings.new_device_link_name or "Link"
        link_id = settings.new_device_link_id or allocate_identifier(base_name, link_ids, fallback="link")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_LINK_KIND
        object_[ENTITY_ID_KEY] = link_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_LINK_ID_KEY] = link_id
        if not settings.device_root_link_id:
            settings.device_root_link_id = link_id
        _report(self, {"INFO"}, f"Created device link {link_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_device_frame(OperatorBase):
    bl_idname = "melos.create_device_frame"
    bl_label = "Create Device Frame"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        frame_ids = _existing_entity_ids(context.scene, DEVICE_FRAME_KIND)
        base_name = settings.new_device_frame_name or "Frame"
        frame_id = settings.new_device_frame_id or allocate_identifier(base_name, frame_ids, fallback="frame")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_FRAME_KIND
        object_[ENTITY_ID_KEY] = frame_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_FRAME_LINK_ID_KEY] = settings.device_frame_link_id or ""
        _report(self, {"INFO"}, f"Created device frame {frame_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_device_joint(OperatorBase):
    bl_idname = "melos.create_device_joint"
    bl_label = "Create Device Joint"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        joint_ids = _existing_entity_ids(context.scene, DEVICE_JOINT_KIND)
        base_name = settings.new_device_joint_name or "Joint"
        joint_id = settings.new_device_joint_id or allocate_identifier(base_name, joint_ids, fallback="joint")
        coordinate_id = settings.device_coordinate_id or allocate_identifier(
            settings.device_coordinate_name or f"{base_name} Coordinate",
            _existing_device_coordinate_ids(context.scene),
            fallback="coordinate",
        )
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_JOINT_KIND
        object_[ENTITY_ID_KEY] = joint_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_JOINT_KIND_KEY] = settings.device_joint_kind or JointKind.REVOLUTE.value
        object_[DEVICE_JOINT_PARENT_LINK_ID_KEY] = settings.device_joint_parent_link_id or ""
        object_[DEVICE_JOINT_CHILD_LINK_ID_KEY] = settings.device_joint_child_link_id or ""
        object_[DEVICE_JOINT_PARENT_FRAME_ID_KEY] = settings.device_joint_parent_frame_id or ""
        object_[DEVICE_JOINT_CHILD_FRAME_ID_KEY] = settings.device_joint_child_frame_id or ""
        object_[JOINT_COORDINATE_ID_KEY] = coordinate_id
        object_[JOINT_COORDINATE_NAME_KEY] = settings.device_coordinate_name or coordinate_id
        object_[JOINT_COORDINATE_KIND_KEY] = settings.device_coordinate_kind or CoordinateKind.ROTATION.value
        object_[JOINT_COORDINATE_AXIS_KEY] = (
            settings.device_coordinate_axis_x,
            settings.device_coordinate_axis_y,
            settings.device_coordinate_axis_z,
        )
        _report(self, {"INFO"}, f"Created device joint {joint_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_device_sensor(OperatorBase):
    bl_idname = "melos.create_device_sensor"
    bl_label = "Create Device Sensor"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        sensor_ids = _existing_entity_ids(context.scene, DEVICE_SENSOR_KIND)
        base_name = settings.new_device_sensor_name or "Sensor"
        sensor_id = settings.new_device_sensor_id or allocate_identifier(base_name, sensor_ids, fallback="sensor")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_SENSOR_KIND
        object_[ENTITY_ID_KEY] = sensor_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_SENSOR_KIND_KEY] = settings.device_sensor_kind or SensorKind.POSITION.value
        object_[DEVICE_SENSOR_FRAME_ID_KEY] = settings.device_sensor_frame_id or ""
        object_[DEVICE_SENSOR_LINK_ID_KEY] = settings.device_sensor_link_id or ""
        _report(self, {"INFO"}, f"Created device sensor {sensor_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_device_actuator(OperatorBase):
    bl_idname = "melos.create_device_actuator"
    bl_label = "Create Device Actuator"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        actuator_ids = _existing_entity_ids(context.scene, DEVICE_ACTUATOR_KIND)
        base_name = settings.new_device_actuator_name or "Actuator"
        actuator_id = settings.new_device_actuator_id or allocate_identifier(base_name, actuator_ids, fallback="actuator")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_ACTUATOR_KIND
        object_[ENTITY_ID_KEY] = actuator_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[DEVICE_ACTUATOR_KIND_KEY] = settings.device_actuator_kind or ActuatorKind.MOTOR.value
        object_[DEVICE_ACTUATOR_JOINT_ID_KEY] = settings.device_actuator_joint_id or ""
        object_[DEVICE_ACTUATOR_COORDINATE_ID_KEY] = settings.device_actuator_coordinate_id or ""
        _report(self, {"INFO"}, f"Created device actuator {actuator_id!r}.")
        return {"FINISHED"}


class MELOS_OT_create_cable_route_point(OperatorBase):
    bl_idname = "melos.create_cable_route_point"
    bl_label = "Create Cable Route Point"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        point_ids = _existing_entity_ids(context.scene, DEVICE_CABLE_ROUTE_POINT_KIND)
        base_name = settings.new_cable_route_name or "Route Point"
        point_id = settings.new_cable_route_id or allocate_identifier(base_name, point_ids, fallback="route_point")
        object_ = _create_empty(context, name=base_name)
        object_[ENTITY_KIND_KEY] = DEVICE_CABLE_ROUTE_POINT_KIND
        object_[ENTITY_ID_KEY] = point_id
        object_[DISPLAY_NAME_KEY] = base_name
        object_[CABLE_ACTUATOR_ID_KEY] = settings.cable_actuator_id or ""
        object_[CABLE_ROUTE_NODE_KIND_KEY] = settings.cable_route_node_kind or RouteNodeKind.SITE.value
        object_[CABLE_ROUTE_ORDER_KEY] = float(settings.cable_route_order)
        object_[CABLE_ROUTE_SITE_ID_KEY] = settings.cable_route_site_id or ""
        object_[CABLE_ROUTE_GEOMETRY_ID_KEY] = settings.cable_route_geometry_id or ""
        object_[CABLE_ROUTE_SIDE_SITE_ID_KEY] = settings.cable_route_side_site_id or ""
        _report(self, {"INFO"}, f"Created cable route point {point_id!r}.")
        return {"FINISHED"}


class MELOS_OT_update_cable_visualization(OperatorBase):
    bl_idname = "melos.update_cable_visualization"
    bl_label = "Update Cable Visualization"

    def execute(self, context):
        _update_all_cable_curves(context.scene)
        _report(self, {"INFO"}, "Updated cable visualizations.")
        return {"FINISHED"}

class MELOS_OT_generate_part(OperatorBase):
    bl_idname = "melos.generate_part"
    bl_label = "Generate Part"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        segment_id = settings.part_target_segment or "limb"

        try:
            from proteus.fitting import build_cuff
        except ImportError:
            _report(self, {"ERROR"}, "proteus is not installed. Install with: uv pip install 'proteus[melos]'")
            return {"CANCELLED"}

        from melos.core.retarget.model import SegmentMeasurementSet, SegmentMeasurement

        measurements = SegmentMeasurementSet(
            items=[SegmentMeasurement(segment_id=segment_id, length=settings.part_limb_circumference)],
            units="m",
        )

        try:
            cuff = build_cuff(
                measurements,
                segment_id,
                coverage=settings.part_coverage,
                width=settings.part_width * 1000,
                wall_thickness=settings.part_wall_thickness * 1000,
                padding_thickness=settings.part_padding_thickness * 1000,
            )
        except Exception as exc:
            _report(self, {"ERROR"}, f"Part generation failed: {exc}")
            return {"CANCELLED"}

        import tempfile, os
        stl_path = os.path.join(tempfile.gettempdir(), f"melos_part_{segment_id}.stl")

        try:
            import build123d as bd
            bd.export_stl(cuff.geom, stl_path)
        except Exception as exc:
            _report(self, {"ERROR"}, f"STL export failed: {exc}")
            return {"CANCELLED"}

        try:
            try:
                bpy.ops.import_mesh.stl(filepath=stl_path)
            except AttributeError:
                bpy.ops.wm.stl_import(filepath=stl_path)
        except Exception as exc:
            _report(self, {"ERROR"}, f"STL import failed: {exc}")
            return {"CANCELLED"}

        obj = context.active_object
        if obj is not None:
            obj[ENTITY_KIND_KEY] = DEVICE_LINK_KIND
            obj[ENTITY_ID_KEY] = segment_id
            obj[DISPLAY_NAME_KEY] = f"{settings.part_type}_{segment_id}"

        _report(self, {"INFO"}, f"Generated {settings.part_type} for segment {segment_id!r}.")
        return {"FINISHED"}


def _update_all_cable_curves(scene):
    """Create or update cable curves for all cable actuators."""
    # Find all cable route points grouped by actuator
    cable_groups = {}
    for obj in scene.objects:
        if obj.get(ENTITY_KIND_KEY) == DEVICE_CABLE_ROUTE_POINT_KIND:
            act_id = obj.get(CABLE_ACTUATOR_ID_KEY)
            if act_id:
                cable_groups.setdefault(act_id, []).append(obj)

    for act_id, route_points in cable_groups.items():
        if len(route_points) < 2:
            continue

        # Sort by order
        route_points.sort(key=lambda obj: obj.get(CABLE_ROUTE_ORDER_KEY, 0))

        # Create or update curve
        curve_name = f"Cable_{act_id}"

        # Check if curve already exists
        if curve_name in bpy.data.objects:
            curve_obj = bpy.data.objects[curve_name]
            curve_data = curve_obj.data
            # Clear existing splines
            curve_data.splines.clear()
        else:
            # Create new curve
            curve_data = bpy.data.curves.new(curve_name, type='CURVE')
            curve_data.dimensions = '3D'
            curve_data.resolution_u = 64
            curve_data.bevel_depth = 0.003
            curve_data.bevel_resolution = 6
            curve_data.fill_mode = 'FULL'

            curve_obj = bpy.data.objects.new(curve_name, curve_data)
            scene.collection.objects.link(curve_obj)

            # Add material
            mat_name = f"Cable_{act_id}_Material"
            if mat_name in bpy.data.materials:
                mat = bpy.data.materials[mat_name]
            else:
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True
                principled = mat.node_tree.nodes.get('Principled BSDF')
                if principled:
                    principled.inputs['Base Color'].default_value = (0.8, 0.1, 0.1, 1.0)
                    principled.inputs['Roughness'].default_value = 0.3
                    principled.inputs['Metallic'].default_value = 0.1

            curve_obj.data.materials.append(mat)

        # Create Bezier spline
        spline = curve_data.splines.new('BEZIER')
        spline.bezier_points.add(len(route_points) - 1)
        spline.resolution_u = 64

        # Set points from route point locations
        for i, rp in enumerate(route_points):
            bp = spline.bezier_points[i]
            bp.co = rp.location
            bp.handle_left = rp.location
            bp.handle_right = rp.location

            # Set handle type based on node kind
            if rp.get(CABLE_ROUTE_NODE_KIND_KEY) == RouteNodeKind.WRAP.value:
                bp.handle_left_type = 'ALIGNED'
                bp.handle_right_type = 'ALIGNED'
            else:
                bp.handle_left_type = 'AUTO'
                bp.handle_right_type = 'AUTO'


# Update cable curves when creating a new route point
_orig_create_cable_route_point = MELOS_OT_create_cable_route_point.execute

def _create_cable_route_point_with_visualization(self, context):
    result = _orig_create_cable_route_point(self, context)
    _update_all_cable_curves(context.scene)
    return result

MELOS_OT_create_cable_route_point.execute = _create_cable_route_point_with_visualization


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


def _existing_device_coordinate_ids(scene) -> set[str]:
    return {
        str(object_.get(JOINT_COORDINATE_ID_KEY))
        for object_ in scene.objects
        if object_.get(ENTITY_KIND_KEY) == DEVICE_JOINT_KIND
        and object_.get(JOINT_COORDINATE_ID_KEY)
    }


def _report(operator: object, level: set[str], message: str) -> None:
    if hasattr(operator, "report"):
        cast(Any, operator).report(level, message)


CLASSES = (
    MELOS_OT_create_device_link,
    MELOS_OT_create_device_frame,
    MELOS_OT_create_device_joint,
    MELOS_OT_create_device_sensor,
    MELOS_OT_create_device_actuator,
    MELOS_OT_create_cable_route_point,
    MELOS_OT_update_cable_visualization,
    MELOS_OT_generate_part,
)

__all__ = [
    "CLASSES",
    "MELOS_OT_create_device_actuator",
    "MELOS_OT_create_cable_route_point",
    "MELOS_OT_update_cable_visualization",
    "MELOS_OT_generate_part",
    "MELOS_OT_create_device_frame",
    "MELOS_OT_create_device_joint",
    "MELOS_OT_create_device_link",
    "MELOS_OT_create_device_sensor",
]

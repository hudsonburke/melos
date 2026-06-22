from __future__ import annotations

import importlib
from typing import Any, Callable

from melos.core.project.model import Project
from melos.core.system.enums import ActuatorKind, GeometryRole, SystemRole

from melos.blender.constants import (
    ASSET_ID_KEY,
    ASSET_NAME_KEY,
    ASSET_ROLE_KEY,
    ASSET_URI_KEY,
    ATTACHMENT_DEVICE_ID_KEY,
    ATTACHMENT_INTERFACE_ID_KEY,
    ATTACHMENT_KIND,
    ATTACHMENT_ANATOMICAL_SITE_ID_KEY,
    DEVICE_ACTUATOR_COORDINATE_ID_KEY,
    DEVICE_ACTUATOR_KIND,
    DEVICE_ACTUATOR_KIND_KEY,
    DEVICE_ACTUATOR_JOINT_ID_KEY,
    CABLE_ACTUATOR_ID_KEY,
    CABLE_ROUTE_GEOMETRY_ID_KEY,
    CABLE_ROUTE_NODE_KIND_KEY,
    CABLE_ROUTE_ORDER_KEY,
    CABLE_ROUTE_SIDE_SITE_ID_KEY,
    CABLE_ROUTE_SITE_ID_KEY,
    DEVICE_CABLE_ROUTE_POINT_KIND,
    DEVICE_FRAME_KIND,
    DEVICE_FRAME_LINK_ID_KEY,
    DEVICE_INTERFACE_ASSET_ID_KEY,
    DEVICE_INTERFACE_FRAME_ID_KEY,
    DEVICE_INTERFACE_KIND,
    DEVICE_INTERFACE_KIND_KEY,
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
    DEVICE_SENSOR_UNIT_KEY,
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    FRAME_LINK_ID_KEY,
    FRAME_IS_ANATOMICAL_KEY,
    JOINT_CHILD_LINK_ID_KEY,
    JOINT_CHILD_FRAME_ID_KEY,
    JOINT_COORDINATE_AXIS_KEY,
    JOINT_COORDINATE_DEFAULT_VALUE_KEY,
    JOINT_COORDINATE_ID_KEY,
    JOINT_COORDINATE_KIND_KEY,
    JOINT_COORDINATE_NAME_KEY,
    JOINT_KIND_KEY,
    JOINT_PARENT_LINK_ID_KEY,
    JOINT_PARENT_FRAME_ID_KEY,
    LANDMARK_BODY_ID_KEY,
    LANDMARK_FRAME_ID_KEY,
    LANDMARK_KIND,
    MUSCLE_ID_KEY,
    MUSCLE_NAME_KEY,
    MUSCLE_PATH_POINT_LINK_ID_KEY,
    MUSCLE_PATH_POINT_SITE_ID_KEY,
    MUSCLE_PATH_POINT_KIND,
    MUSCLE_PATH_POINT_KIND_KEY,
    MUSCLE_PATH_POINT_ORDER_KEY,
    MUSCLE_WRAP_LINK_ID_KEY,
    MUSCLE_WRAP_SITE_ID_KEY,
    MUSCLE_WRAP_GEOMETRY_KIND,
    MUSCLE_WRAP_HEIGHT_KEY,
    MUSCLE_WRAP_KIND_KEY,
    MUSCLE_WRAP_RADIUS_KEY,
    ANATOMICAL_LINK_ASSET_KIND,
    ANATOMICAL_LINK_KIND,
    ANATOMICAL_SITE_KIND,
    ANATOMICAL_JOINT_KIND,
)


try:
    bpy = importlib.import_module("bpy")
except ModuleNotFoundError:
    bpy = None


def _default_create_object(name: str, collection: Any) -> Any:  # pragma: no cover
    if bpy is None:  # pragma: no cover
        raise RuntimeError("The melos add-on can only create objects inside Blender.")
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    collection.objects.link(obj)
    return obj

def _load_stl_mesh_data(path: str) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]] | None:
    """Read a binary STL file and return (vertices, faces) or None on failure."""
    import os
    import struct
    if not os.path.isfile(path):
        return None
    try:
        data = open(path, "rb").read()
        triangle_count = struct.unpack_from("<I", data, 80)[0]
        offset = 84
        vertices: list[tuple[float, float, float]] = []
        faces: list[tuple[int, int, int]] = []
        for _ in range(triangle_count):
            if offset + 50 > len(data):
                break
            offset += 12  # skip normal
            v0 = struct.unpack_from("<fff", data, offset)
            v1 = struct.unpack_from("<fff", data, offset + 12)
            v2 = struct.unpack_from("<fff", data, offset + 24)
            base = len(vertices)
            vertices.extend([v0, v1, v2])
            faces.append((base, base + 1, base + 2))
            offset += 36 + 2  # 3 vertices + attribute byte
        return vertices, faces
    except Exception:
        return None


def _create_mesh_object(name: str, vertices: list, faces: list, collection: Any) -> Any | None:
    """Create a Blender mesh object from vertex/face data."""
    if bpy is None:
        return None
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [list(v) for v in vertices],
        [],
        [list(f) for f in faces],
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def _import_mesh_asset(uri: str, name: str, collection: Any) -> Any | None:
    """Import a mesh file into Blender and return the created object."""
    if bpy is None:
        return None
    data = _load_stl_mesh_data(uri)
    if data is None:
        return None
    vertices, faces = data
    if not vertices or not faces:
        return None
    obj = _create_mesh_object(name, vertices, faces, collection)
    if obj is not None:
        obj[ASSET_URI_KEY] = uri
    return obj


def import_project_to_scene(
    project: Project,
    scene: Any,
    settings: Any,
    *,
    create_object: Callable[[str, Any], Any] | None = None,
    load_meshes: bool = True,
) -> list[Any]:
    if create_object is None:
        create_object = _default_create_object  # pragma: no cover

    collection = getattr(scene, "collection", scene)
    created: list[Any] = []

    def _make(name: str) -> Any:
        obj = create_object(name, collection)
        created.append(obj)
        return obj

    link_objects: dict[tuple[str, str], Any] = {}

    for system in project.systems:
        for link in system.links:
            obj = _make(link.name)
            obj[ENTITY_KIND_KEY] = ANATOMICAL_LINK_KIND if system.role == SystemRole.ANATOMICAL else DEVICE_LINK_KIND
            obj[ENTITY_ID_KEY] = link.id
            obj[DISPLAY_NAME_KEY] = link.name
            if system.role != SystemRole.ANATOMICAL:
                obj[DEVICE_LINK_ID_KEY] = link.id
            _apply_transform(obj, link.transform)
            if hasattr(obj, "empty_display_size"):
                obj.empty_display_size = 0.02
            link_objects[(system.id, link.id)] = obj

        # Parent links according to joint hierarchy
        for joint in system.joints:
            child_link_id = joint.child_link_id
            parent_link_id = joint.parent_link_id
            if not child_link_id or not parent_link_id:
                continue
            child_obj = link_objects.get((system.id, child_link_id))
            parent_obj = link_objects.get((system.id, parent_link_id))
            if child_obj is not None and parent_obj is not None:
                _set_parent(child_obj, parent_obj)

        # Load visual mesh assets for links
        if load_meshes:
            asset_by_id = {a.id: a for a in project.assets.items}
            for link in system.links:
                if not link.asset_ids:
                    continue
                link_obj = link_objects.get((system.id, link.id))
                if link_obj is None:
                    continue
                for asset_id in link.asset_ids:
                    asset = asset_by_id.get(asset_id)
                    if asset is None:
                        continue
                    # Only import visual assets as mesh objects
                    if str(asset.role) != "visual":
                        continue
                    mesh_obj = _import_mesh_asset(asset.uri, f"{link.name}_mesh", collection)
                    if mesh_obj is not None:
                        mesh_obj[ENTITY_KIND_KEY] = ANATOMICAL_LINK_ASSET_KIND
                        mesh_obj[ASSET_ID_KEY] = asset.id
                        mesh_obj[ASSET_NAME_KEY] = asset.name
                        mesh_obj[ASSET_ROLE_KEY] = str(asset.role)
                        mesh_obj[ASSET_URI_KEY] = asset.uri
                        _apply_transform(mesh_obj, link.transform)
                        _set_parent_inherit(mesh_obj, link_obj)

        for joint in system.joints:
            if system.role == SystemRole.ANATOMICAL:
                obj = _make(joint.name)
                obj[ENTITY_KIND_KEY] = ANATOMICAL_JOINT_KIND
                obj[ENTITY_ID_KEY] = joint.id
                obj[DISPLAY_NAME_KEY] = joint.name
                obj[JOINT_KIND_KEY] = joint.kind.value
                obj[JOINT_PARENT_LINK_ID_KEY] = joint.parent_link_id or ""
                obj[JOINT_CHILD_LINK_ID_KEY] = joint.child_link_id
                obj[JOINT_PARENT_FRAME_ID_KEY] = joint.parent_site_id or ""
                obj[JOINT_CHILD_FRAME_ID_KEY] = joint.child_site_id or ""
                _apply_coordinate_properties(obj, joint)
            else:
                obj = _make(joint.name)
                obj[ENTITY_KIND_KEY] = DEVICE_JOINT_KIND
                obj[ENTITY_ID_KEY] = joint.id
                obj[DISPLAY_NAME_KEY] = joint.name
                obj[DEVICE_JOINT_KIND_KEY] = joint.kind.value
                obj[DEVICE_JOINT_PARENT_LINK_ID_KEY] = joint.parent_link_id or ""
                obj[DEVICE_JOINT_CHILD_LINK_ID_KEY] = joint.child_link_id
                obj[DEVICE_JOINT_PARENT_FRAME_ID_KEY] = joint.parent_site_id or ""
                obj[DEVICE_JOINT_CHILD_FRAME_ID_KEY] = joint.child_site_id or ""
                _apply_coordinate_properties(obj, joint)
            if hasattr(obj, "hide_viewport"):
                obj.hide_viewport = True
            if hasattr(obj, "hide_render"):
                obj.hide_render = True

        muscle_order_by_site_id = _muscle_site_metadata(system)
        for site in system.sites:
            if system.role == SystemRole.ANATOMICAL and "landmark" in site.tags:
                obj = _make(site.name)
                obj[ENTITY_KIND_KEY] = LANDMARK_KIND
                obj[ENTITY_ID_KEY] = site.id
                obj[DISPLAY_NAME_KEY] = site.name
                obj[LANDMARK_BODY_ID_KEY] = site.link_id or ""
                obj[LANDMARK_FRAME_ID_KEY] = site.parent_site_id or ""
                _apply_transform(obj, site.transform)
                if hasattr(obj, "hide_viewport"):
                    obj.hide_viewport = True
                if hasattr(obj, "hide_render"):
                    obj.hide_render = True
            elif system.role == SystemRole.ANATOMICAL and "muscle_path_point" in site.tags:
                obj = _make(site.name)
                obj[ENTITY_KIND_KEY] = MUSCLE_PATH_POINT_KIND
                obj[ENTITY_ID_KEY] = site.id
                obj[DISPLAY_NAME_KEY] = site.name
                muscle_id, order, point_kind = muscle_order_by_site_id.get(site.id, ("", 0, "via"))
                obj[MUSCLE_ID_KEY] = muscle_id
                obj[MUSCLE_NAME_KEY] = muscle_id
                obj[MUSCLE_PATH_POINT_KIND_KEY] = point_kind
                obj[MUSCLE_PATH_POINT_LINK_ID_KEY] = site.link_id or ""
                obj[MUSCLE_PATH_POINT_SITE_ID_KEY] = site.parent_site_id or ""
                obj[MUSCLE_PATH_POINT_ORDER_KEY] = order
                _apply_transform(obj, site.transform)
                if hasattr(obj, "hide_viewport"):
                    obj.hide_viewport = True
                if hasattr(obj, "hide_render"):
                    obj.hide_render = True
            elif not (system.role != SystemRole.ANATOMICAL and "interface" in site.tags):
                obj = _make(site.name)
                obj[ENTITY_KIND_KEY] = ANATOMICAL_SITE_KIND if system.role == SystemRole.ANATOMICAL else DEVICE_FRAME_KIND
                obj[ENTITY_ID_KEY] = site.id
                obj[DISPLAY_NAME_KEY] = site.name
                if system.role == SystemRole.ANATOMICAL:
                    obj[FRAME_LINK_ID_KEY] = site.link_id or ""
                    obj[FRAME_IS_ANATOMICAL_KEY] = "anatomical" in site.tags
                else:
                    obj[DEVICE_FRAME_LINK_ID_KEY] = site.link_id or ""
                _apply_transform(obj, site.transform)
                if hasattr(obj, "hide_viewport"):
                    obj.hide_viewport = True
                if hasattr(obj, "hide_render"):
                    obj.hide_render = True
                if site.link_id:
                    parent = link_objects.get((system.id, site.link_id))
                    if parent is not None:
                        _set_parent(obj, parent)

        if system.role == SystemRole.ANATOMICAL:
            for geometry in system.geometries:
                if geometry.role != GeometryRole.WRAP:
                    continue
                obj = _make(geometry.name)
                obj[ENTITY_KIND_KEY] = MUSCLE_WRAP_GEOMETRY_KIND
                obj[ENTITY_ID_KEY] = geometry.id
                obj[DISPLAY_NAME_KEY] = geometry.name
                obj[MUSCLE_WRAP_KIND_KEY] = geometry.kind
                obj[MUSCLE_WRAP_LINK_ID_KEY] = geometry.link_id or ""
                obj[MUSCLE_WRAP_SITE_ID_KEY] = geometry.site_id or ""
                if "radius" in geometry.parameters:
                    obj[MUSCLE_WRAP_RADIUS_KEY] = geometry.parameters["radius"]
                if "height" in geometry.parameters:
                    obj[MUSCLE_WRAP_HEIGHT_KEY] = geometry.parameters["height"]
                _apply_transform(obj, geometry.transform)
                if hasattr(obj, "hide_viewport"):
                    obj.hide_viewport = True
                if hasattr(obj, "hide_render"):
                    obj.hide_render = True
                if geometry.link_id:
                    parent = link_objects.get((system.id, geometry.link_id))
                    if parent is not None:
                        _set_parent(obj, parent)
        else:
            for sensor in system.sensors:
                obj = _make(sensor.name)
                obj[ENTITY_KIND_KEY] = DEVICE_SENSOR_KIND
                obj[ENTITY_ID_KEY] = sensor.id
                obj[DISPLAY_NAME_KEY] = sensor.name
                obj[DEVICE_SENSOR_KIND_KEY] = sensor.kind.value
                obj[DEVICE_SENSOR_FRAME_ID_KEY] = sensor.site_id or ""
                obj[DEVICE_SENSOR_LINK_ID_KEY] = sensor.link_id or ""
                obj[DEVICE_SENSOR_UNIT_KEY] = sensor.measurement_unit
            for actuator in system.actuators:
                if actuator.kind == ActuatorKind.MUSCLE:
                    continue
                obj = _make(actuator.name)
                obj[ENTITY_KIND_KEY] = DEVICE_ACTUATOR_KIND
                obj[ENTITY_ID_KEY] = actuator.id
                obj[DISPLAY_NAME_KEY] = actuator.name
                obj[DEVICE_ACTUATOR_KIND_KEY] = actuator.kind.value
                obj[DEVICE_ACTUATOR_JOINT_ID_KEY] = actuator.joint_id or ""
                obj[DEVICE_ACTUATOR_COORDINATE_ID_KEY] = actuator.coordinate_id or ""
                for order, node in enumerate(actuator.route):
                    point = _make(f"{actuator.name} Route {order}")
                    point[ENTITY_KIND_KEY] = DEVICE_CABLE_ROUTE_POINT_KIND
                    point[ENTITY_ID_KEY] = f"{actuator.id}_route_{order}"
                    point[DISPLAY_NAME_KEY] = f"{actuator.name} Route {order}"
                    point[CABLE_ACTUATOR_ID_KEY] = actuator.id
                    point[CABLE_ROUTE_ORDER_KEY] = float(order)
                    point[CABLE_ROUTE_NODE_KIND_KEY] = node.kind.value
                    point[CABLE_ROUTE_SITE_ID_KEY] = node.site_id or ""
                    point[CABLE_ROUTE_GEOMETRY_ID_KEY] = node.geometry_id or ""
                    point[CABLE_ROUTE_SIDE_SITE_ID_KEY] = node.side_site_id or ""
            for site in system.sites:
                if "interface" not in site.tags:
                    continue
                obj = _make(site.name)
                obj[ENTITY_KIND_KEY] = DEVICE_INTERFACE_KIND
                obj[ENTITY_ID_KEY] = site.id
                obj[DISPLAY_NAME_KEY] = site.name
                obj[DEVICE_INTERFACE_KIND_KEY] = str(site.annotations.get("interface_kind", "custom"))
                obj[DEVICE_INTERFACE_FRAME_ID_KEY] = site.parent_site_id or ""
                obj[DEVICE_INTERFACE_ASSET_ID_KEY] = str(site.annotations.get("interface_asset_id", ""))
                _apply_transform(obj, site.transform)

    for assembly in project.assemblies:
        for connection in assembly.connections:
            endpoints = [connection.endpoint_a, connection.endpoint_b]
            device_endpoint = None
            anatomical_endpoint = None
            for endpoint in endpoints:
                if endpoint is None:
                    continue
                system = project.get_system(endpoint.system_id)
                if system is None:
                    continue
                if system.role == SystemRole.ANATOMICAL:
                    anatomical_endpoint = endpoint
                else:
                    device_endpoint = endpoint
            if device_endpoint is None:
                continue
            obj = _make(connection.name)
            obj[ENTITY_KIND_KEY] = ATTACHMENT_KIND
            obj[ENTITY_ID_KEY] = connection.id
            obj[DISPLAY_NAME_KEY] = connection.name
            obj[ATTACHMENT_DEVICE_ID_KEY] = device_endpoint.system_id
            obj[ATTACHMENT_INTERFACE_ID_KEY] = device_endpoint.reference_site_ids[0] if device_endpoint.reference_site_ids else ""
            obj[ATTACHMENT_ANATOMICAL_SITE_ID_KEY] = anatomical_endpoint.reference_site_ids[0] if anatomical_endpoint is not None and anatomical_endpoint.reference_site_ids else ""
            _apply_transform(obj, connection.relative_transform)

    settings.project_id = project.meta.id
    settings.project_name = project.meta.name
    anatomical_system = next((system for system in project.systems if system.role == SystemRole.ANATOMICAL), None)
    if anatomical_system is not None:
        settings.anatomical_system_id = anatomical_system.id
        settings.anatomical_system_name = anatomical_system.name
        settings.anatomical_system_root_link_id = anatomical_system.root_link_id or ""

    return created


def _apply_coordinate_properties(obj: Any, joint: Any) -> None:
    if not joint.coordinates:
        return
    coordinate = joint.coordinates[0]
    obj[JOINT_COORDINATE_ID_KEY] = coordinate.id
    obj[JOINT_COORDINATE_NAME_KEY] = coordinate.name
    obj[JOINT_COORDINATE_KIND_KEY] = coordinate.kind.value
    obj[JOINT_COORDINATE_AXIS_KEY] = tuple(coordinate.axis)
    obj[JOINT_COORDINATE_DEFAULT_VALUE_KEY] = coordinate.default_value


def _muscle_site_metadata(system: Any) -> dict[str, tuple[str, int, str]]:
    metadata: dict[str, tuple[str, int, str]] = {}
    for actuator in system.actuators:
        if actuator.kind != ActuatorKind.MUSCLE:
            continue
        for index, site_id in enumerate(actuator.site_ids):
            point_kind = "via"
            if actuator.site_ids:
                if index == 0:
                    point_kind = "origin"
                elif index == len(actuator.site_ids) - 1:
                    point_kind = "insertion"
            metadata[site_id] = (actuator.id, index, point_kind)
    return metadata


def _apply_transform(obj: Any, transform: Any) -> None:
    translation = getattr(transform, "translation", None)
    rotation = getattr(transform, "rotation", None)
    if translation is not None and hasattr(obj, "location"):
        obj.location = tuple(float(v) for v in translation)
    if rotation is not None:
        if hasattr(obj, "rotation_mode"):
            obj.rotation_mode = "QUATERNION"
        if hasattr(obj, "rotation_quaternion"):
            obj.rotation_quaternion = tuple(float(v) for v in rotation)


def _set_parent(child: Any, parent: Any) -> None:
    child.parent = parent
    # Preserve the child's world transform when parenting.
    # Without matrix_parent_inverse, Blender reinterprets the child's
    # local transform in the parent's coordinate space, moving it in world.
    child_matrix_world = getattr(child, "matrix_world", None)
    parent_matrix_world = getattr(parent, "matrix_world", None)
    if child_matrix_world is not None and parent_matrix_world is not None:
        inverted = getattr(parent_matrix_world, "inverted", None)
        if callable(inverted):
            child.matrix_parent_inverse = inverted()
    children = getattr(parent, "children", None)
    if isinstance(children, list) and child not in children:
        children.append(child)


def _set_parent_inherit(child: Any, parent: Any) -> None:
    """Parent child to parent WITHOUT preserving world transform.

    The child inherits the parent's transform directly. Use this when
    the child's local transform should be interpreted in the parent's
    coordinate space (e.g. mesh objects positioned at a link's location).
    """
    child.parent = parent
    children = getattr(parent, "children", None)
    if isinstance(children, list) and child not in children:
        children.append(child)


__all__ = ["import_project_to_scene"]

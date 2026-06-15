"""Shared constants for the Blender authoring frontend."""

from __future__ import annotations

ADDON_NAME = "melos"
SCENE_SETTINGS_ATTRIBUTE = "melos_blender"

ENTITY_KIND_KEY = "melos_entity_kind"
ENTITY_ID_KEY = "melos_id"
DISPLAY_NAME_KEY = "melos_name"
ASSET_ID_KEY = "melos_asset_id"
ASSET_NAME_KEY = "melos_asset_name"
ASSET_ROLE_KEY = "melos_asset_role"
ASSET_URI_KEY = "melos_asset_uri"

ANATOMICAL_LINK_KIND = "anatomical_link"
ANATOMICAL_SITE_KIND = "anatomical_site"
ANATOMICAL_JOINT_KIND = "anatomical_joint"
ANATOMICAL_LINK_ASSET_KIND = "anatomical_link_asset"

BODY_MASS_KEY = "melos_mass"
BODY_CENTER_OF_MASS_KEY = "melos_center_of_mass"
BODY_INERTIA_KEY = "melos_inertia_about_com"

FRAME_LINK_ID_KEY = "melos_link_id"
FRAME_IS_ANATOMICAL_KEY = "melos_is_anatomical"

JOINT_KIND_KEY = "melos_joint_kind"
JOINT_PARENT_LINK_ID_KEY = "melos_parent_link_id"
JOINT_CHILD_LINK_ID_KEY = "melos_child_link_id"
JOINT_PARENT_FRAME_ID_KEY = "melos_parent_frame_id"
JOINT_CHILD_FRAME_ID_KEY = "melos_child_frame_id"
JOINT_COORDINATE_ID_KEY = "melos_coordinate_id"
JOINT_COORDINATE_NAME_KEY = "melos_coordinate_name"
JOINT_COORDINATE_KIND_KEY = "melos_coordinate_kind"
JOINT_COORDINATE_AXIS_KEY = "melos_coordinate_axis"
JOINT_COORDINATE_DEFAULT_VALUE_KEY = "melos_coordinate_default_value"

BLENDER_SUPPORTED_MAJOR_MINOR = (4, 1)

# Device entity kinds
DEVICE_LINK_KIND = "device_link"
DEVICE_FRAME_KIND = "device_frame"
DEVICE_JOINT_KIND = "device_joint"
DEVICE_SENSOR_KIND = "device_sensor"
DEVICE_ACTUATOR_KIND = "device_actuator"
DEVICE_INTERFACE_KIND = "device_interface"

# Device property keys
DEVICE_LINK_ID_KEY = "melos_device_link_id"
DEVICE_FRAME_LINK_ID_KEY = "melos_device_frame_link_id"
DEVICE_JOINT_KIND_KEY = "melos_device_joint_kind"
DEVICE_JOINT_PARENT_LINK_ID_KEY = "melos_device_joint_parent_link_id"
DEVICE_JOINT_CHILD_LINK_ID_KEY = "melos_device_joint_child_link_id"
DEVICE_JOINT_PARENT_FRAME_ID_KEY = "melos_device_joint_parent_frame_id"
DEVICE_JOINT_CHILD_FRAME_ID_KEY = "melos_device_joint_child_frame_id"
DEVICE_SENSOR_KIND_KEY = "melos_device_sensor_kind"
DEVICE_SENSOR_FRAME_ID_KEY = "melos_device_sensor_frame_id"
DEVICE_SENSOR_LINK_ID_KEY = "melos_device_sensor_link_id"
DEVICE_SENSOR_UNIT_KEY = "melos_device_sensor_unit"
DEVICE_ACTUATOR_KIND_KEY = "melos_device_actuator_kind"
DEVICE_ACTUATOR_JOINT_ID_KEY = "melos_device_actuator_joint_id"
DEVICE_ACTUATOR_COORDINATE_ID_KEY = "melos_device_actuator_coordinate_id"
DEVICE_INTERFACE_KIND_KEY = "melos_device_interface_kind"
DEVICE_INTERFACE_FRAME_ID_KEY = "melos_device_interface_frame_id"
DEVICE_INTERFACE_ASSET_ID_KEY = "melos_device_interface_asset_id"

# Muscle entity kinds
MUSCLE_PATH_POINT_KIND = "muscle_path_point"
MUSCLE_WRAP_GEOMETRY_KIND = "muscle_wrap_geometry"

# Muscle property keys
MUSCLE_ID_KEY = "melos_muscle_id"
MUSCLE_NAME_KEY = "melos_muscle_name"
MUSCLE_PATH_POINT_KIND_KEY = "melos_muscle_pp_kind"
MUSCLE_PATH_POINT_LINK_ID_KEY = "melos_muscle_pp_link_id"
MUSCLE_PATH_POINT_SITE_ID_KEY = "melos_muscle_pp_site_id"
MUSCLE_PATH_POINT_ORDER_KEY = "melos_muscle_pp_order"
MUSCLE_WRAP_KIND_KEY = "melos_wrap_kind"
MUSCLE_WRAP_LINK_ID_KEY = "melos_wrap_link_id"
MUSCLE_WRAP_SITE_ID_KEY = "melos_wrap_site_id"
MUSCLE_WRAP_RADIUS_KEY = "melos_wrap_radius"
MUSCLE_WRAP_HEIGHT_KEY = "melos_wrap_height"

# Cable routing entity kinds
DEVICE_CABLE_ROUTE_POINT_KIND = "device_cable_route_point"

# Cable routing property keys
CABLE_ACTUATOR_ID_KEY = "melos_cable_actuator_id"
CABLE_ROUTE_ORDER_KEY = "melos_cable_route_order"
CABLE_ROUTE_NODE_KIND_KEY = "melos_cable_route_node_kind"
CABLE_ROUTE_SITE_ID_KEY = "melos_cable_route_site_id"
CABLE_ROUTE_GEOMETRY_ID_KEY = "melos_cable_route_geometry_id"
CABLE_ROUTE_SIDE_SITE_ID_KEY = "melos_cable_route_side_site_id"

# Assembly entity kinds
ATTACHMENT_KIND = "attachment"

# Assembly property keys
ATTACHMENT_DEVICE_ID_KEY = "melos_attachment_device_id"
ATTACHMENT_INTERFACE_ID_KEY = "melos_attachment_interface_id"
ATTACHMENT_ANATOMICAL_SITE_ID_KEY = "melos_attachment_anatomical_site_id"

# Landmark entity kinds
LANDMARK_KIND = "landmark"

# Landmark property keys
LANDMARK_BODY_ID_KEY = "melos_landmark_body_id"
LANDMARK_FRAME_ID_KEY = "melos_landmark_frame_id"

__all__ = [
    "ADDON_NAME",
    "ASSET_ID_KEY",
    "ASSET_NAME_KEY",
    "ASSET_ROLE_KEY",
    "ASSET_URI_KEY",
    "BLENDER_SUPPORTED_MAJOR_MINOR",
    "BODY_CENTER_OF_MASS_KEY",
    "BODY_INERTIA_KEY",
    "BODY_MASS_KEY",
    "DEVICE_ACTUATOR_COORDINATE_ID_KEY",
    "DEVICE_ACTUATOR_KIND",
    "DEVICE_ACTUATOR_KIND_KEY",
    "DEVICE_ACTUATOR_JOINT_ID_KEY",
    "DEVICE_FRAME_KIND",
    "DEVICE_FRAME_LINK_ID_KEY",
    "DEVICE_INTERFACE_ASSET_ID_KEY",
    "DEVICE_INTERFACE_FRAME_ID_KEY",
    "DEVICE_INTERFACE_KIND",
    "DEVICE_INTERFACE_KIND_KEY",
    "DEVICE_JOINT_CHILD_FRAME_ID_KEY",
    "DEVICE_JOINT_CHILD_LINK_ID_KEY",
    "DEVICE_JOINT_KIND",
    "DEVICE_JOINT_KIND_KEY",
    "DEVICE_JOINT_PARENT_FRAME_ID_KEY",
    "DEVICE_JOINT_PARENT_LINK_ID_KEY",
    "DEVICE_LINK_ID_KEY",
    "DEVICE_LINK_KIND",
    "DEVICE_SENSOR_FRAME_ID_KEY",
    "DEVICE_SENSOR_KIND",
    "DEVICE_SENSOR_KIND_KEY",
    "DEVICE_SENSOR_LINK_ID_KEY",
    "DEVICE_SENSOR_UNIT_KEY",
    "DISPLAY_NAME_KEY",
    "ENTITY_ID_KEY",
    "ENTITY_KIND_KEY",
    "FRAME_LINK_ID_KEY",
    "FRAME_IS_ANATOMICAL_KEY",
    "JOINT_CHILD_LINK_ID_KEY",
    "JOINT_CHILD_FRAME_ID_KEY",
    "JOINT_COORDINATE_AXIS_KEY",
    "JOINT_COORDINATE_DEFAULT_VALUE_KEY",
    "JOINT_COORDINATE_ID_KEY",
    "JOINT_COORDINATE_KIND_KEY",
    "JOINT_COORDINATE_NAME_KEY",
    "JOINT_KIND_KEY",
    "JOINT_PARENT_LINK_ID_KEY",
    "JOINT_PARENT_FRAME_ID_KEY",
    "SCENE_SETTINGS_ATTRIBUTE",
    "ANATOMICAL_LINK_ASSET_KIND",
    "ANATOMICAL_LINK_KIND",
    "ANATOMICAL_SITE_KIND",
    "ANATOMICAL_JOINT_KIND",
    "MUSCLE_PATH_POINT_KIND",
    "MUSCLE_WRAP_GEOMETRY_KIND",
    "MUSCLE_ID_KEY",
    "MUSCLE_NAME_KEY",
    "MUSCLE_PATH_POINT_KIND_KEY",
    "MUSCLE_PATH_POINT_LINK_ID_KEY",
    "MUSCLE_PATH_POINT_SITE_ID_KEY",
    "MUSCLE_PATH_POINT_ORDER_KEY",
    "MUSCLE_WRAP_KIND_KEY",
    "MUSCLE_WRAP_LINK_ID_KEY",
    "MUSCLE_WRAP_SITE_ID_KEY",
    "MUSCLE_WRAP_RADIUS_KEY",
    "MUSCLE_WRAP_HEIGHT_KEY",
    "DEVICE_CABLE_ROUTE_POINT_KIND",
    "CABLE_ACTUATOR_ID_KEY",
    "CABLE_ROUTE_ORDER_KEY",
    "CABLE_ROUTE_NODE_KIND_KEY",
    "CABLE_ROUTE_SITE_ID_KEY",
    "CABLE_ROUTE_GEOMETRY_ID_KEY",
    "CABLE_ROUTE_SIDE_SITE_ID_KEY",
    "ATTACHMENT_KIND",
    "ATTACHMENT_DEVICE_ID_KEY",
    "ATTACHMENT_INTERFACE_ID_KEY",
    "ATTACHMENT_ANATOMICAL_SITE_ID_KEY",
    "LANDMARK_KIND",
    "LANDMARK_BODY_ID_KEY",
    "LANDMARK_FRAME_ID_KEY",
]

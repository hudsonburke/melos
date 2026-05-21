from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from melos.core.common.types import Bounds
from melos.core.kinematics.enums import CoordinateKind, JointKind
from melos.core.kinematics.model import CoordinateDefinition
from melos.core.system.enums import ActuatorKind, InterfaceKind, SensorKind, SystemRole
from melos.core.system.model import Actuator, Joint, Link, Sensor, Site, SystemModel

from melos.blender.constants import (
    DEVICE_ACTUATOR_COORDINATE_ID_KEY,
    DEVICE_ACTUATOR_KIND,
    DEVICE_ACTUATOR_KIND_KEY,
    DEVICE_ACTUATOR_JOINT_ID_KEY,
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
)
from melos.blender.services.builders import build_system_model

from .transforms import transform_from_object


def build_device_from_scene(scene: object, settings: object) -> SystemModel:
    link_objects = list(_iter_scene_objects(scene, DEVICE_LINK_KIND))
    frame_objects = list(_iter_scene_objects(scene, DEVICE_FRAME_KIND))
    joint_objects = list(_iter_scene_objects(scene, DEVICE_JOINT_KIND))
    sensor_objects = list(_iter_scene_objects(scene, DEVICE_SENSOR_KIND))
    actuator_objects = list(_iter_scene_objects(scene, DEVICE_ACTUATOR_KIND))
    interface_objects = list(_iter_scene_objects(scene, DEVICE_INTERFACE_KIND))

    links = [_build_device_link(obj) for obj in link_objects]
    sites = [_build_device_frame(obj) for obj in frame_objects]
    sites.extend(_build_device_interface_site(obj) for obj in interface_objects)
    joints = [_build_device_joint(obj) for obj in joint_objects]
    sensors = [_build_device_sensor(obj) for obj in sensor_objects]
    actuators = [_build_device_actuator(obj) for obj in actuator_objects]

    root_link_id = getattr(settings, "device_root_link_id", None) or None
    return build_system_model(
        system_id=getattr(settings, "device_id", "device"),
        name=getattr(settings, "device_name", "device"),
        role=SystemRole.DEVICE,
        root_link_id=root_link_id,
        links=links,
        sites=sites,
        joints=joints,
        sensors=sensors,
        actuators=actuators,
    )


def _build_device_link(object_: object) -> Link:
    return Link(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
    )


def _build_device_frame(object_: object) -> Site:
    return Site(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        link_id=_optional_string(object_, DEVICE_FRAME_LINK_ID_KEY),
        transform=transform_from_object(object_, use_local=True),
        tags=["frame"],
    )


def _build_device_joint(object_: object) -> Joint:
    parent_link_id = _optional_string(object_, DEVICE_JOINT_PARENT_LINK_ID_KEY)
    child_link_id = _optional_string(object_, DEVICE_JOINT_CHILD_LINK_ID_KEY)
    if child_link_id is None:
        raise ValueError(
            f"Device joint {_required_string(object_, ENTITY_ID_KEY)!r} is missing a child link reference."
        )
    return Joint(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        kind=JointKind(
            getattr(object_, "get", lambda *_: JointKind.REVOLUTE.value)(
                DEVICE_JOINT_KIND_KEY, JointKind.REVOLUTE.value
            )
        ),
        parent_link_id=parent_link_id,
        child_link_id=child_link_id,
        parent_site_id=_optional_string(object_, DEVICE_JOINT_PARENT_FRAME_ID_KEY),
        child_site_id=_optional_string(object_, DEVICE_JOINT_CHILD_FRAME_ID_KEY),
        coordinates=[_build_coordinate_definition(object_)],
    )


def _build_device_sensor(object_: object) -> Sensor:
    return Sensor(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        kind=SensorKind(
            getattr(object_, "get", lambda *_: SensorKind.POSITION.value)(
                DEVICE_SENSOR_KIND_KEY, SensorKind.POSITION.value
            )
        ),
        site_id=_optional_string(object_, DEVICE_SENSOR_FRAME_ID_KEY),
        link_id=_optional_string(object_, DEVICE_SENSOR_LINK_ID_KEY),
    )


def _build_device_actuator(object_: object) -> Actuator:
    return Actuator(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        kind=ActuatorKind(
            getattr(object_, "get", lambda *_: ActuatorKind.MOTOR.value)(
                DEVICE_ACTUATOR_KIND_KEY, ActuatorKind.MOTOR.value
            )
        ),
        joint_id=_optional_string(object_, DEVICE_ACTUATOR_JOINT_ID_KEY),
        coordinate_id=_optional_string(object_, DEVICE_ACTUATOR_COORDINATE_ID_KEY),
    )


def _build_device_interface_site(object_: object) -> Site:
    kind = getattr(object_, "get", lambda *_: InterfaceKind.CUSTOM.value)(
        DEVICE_INTERFACE_KIND_KEY,
        InterfaceKind.CUSTOM.value,
    )
    tags = ["interface", str(InterfaceKind(kind))]
    asset_id = _optional_string(object_, DEVICE_INTERFACE_ASSET_ID_KEY)
    annotations = {"interface_kind": str(InterfaceKind(kind))}
    if asset_id is not None:
        annotations["interface_asset_id"] = asset_id
    return Site(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        link_id=_optional_string(object_, DEVICE_FRAME_LINK_ID_KEY),
        parent_site_id=_optional_string(object_, DEVICE_INTERFACE_FRAME_ID_KEY),
        transform=transform_from_object(object_, use_local=True),
        tags=tags,
        annotations=annotations,
    )


def _build_coordinate_definition(object_: object) -> CoordinateDefinition:
    coordinate_id = _required_string(object_, JOINT_COORDINATE_ID_KEY)
    coordinate_name = _optional_string(object_, JOINT_COORDINATE_NAME_KEY) or coordinate_id
    coordinate_kind = CoordinateKind(
        getattr(object_, "get", lambda *_: CoordinateKind.ROTATION.value)(
            JOINT_COORDINATE_KIND_KEY,
            CoordinateKind.ROTATION.value,
        )
    )
    axis = _tuple3(
        getattr(object_, "get", lambda *_: (1.0, 0.0, 0.0))(
            JOINT_COORDINATE_AXIS_KEY,
            (1.0, 0.0, 0.0),
        )
    )
    return CoordinateDefinition(
        id=coordinate_id,
        name=coordinate_name,
        kind=coordinate_kind,
        axis=axis,
        default_value=0.0,
        limits=Bounds(),
    )


def _iter_scene_objects(scene: object, entity_kind: str) -> list[object]:
    objects = getattr(scene, "objects", None)
    if objects is None:
        raise ValueError("Expected a Blender scene with an 'objects' collection.")
    return [
        object_
        for object_ in objects
        if getattr(object_, "get", lambda *_: None)(ENTITY_KIND_KEY) == entity_kind
    ]


def _preferred_name(object_: object) -> str:
    return _optional_string(object_, DISPLAY_NAME_KEY) or getattr(object_, "name", "unnamed")


def _required_string(object_: object, key: str) -> str:
    value = _optional_string(object_, key)
    if value is None:
        raise ValueError(
            f"Expected Blender object {getattr(object_, 'name', '<unnamed>')!r} to define {key!r}."
        )
    return value


def _optional_string(object_: object, key: str) -> str | None:
    value = getattr(object_, "get", lambda *_: None)(key)
    if value in (None, ""):
        return None
    return str(value)


def _tuple3(value: Iterable[object]) -> tuple[float, float, float]:
    components = tuple(float(cast(float | int | str, component)) for component in value)
    if len(components) != 3:
        raise ValueError(f"Expected 3 components, received {len(components)}.")
    return components  # type: ignore[return-value]

from __future__ import annotations

from melos.blender.bpy_io.device import build_device_from_scene
from melos.core.common.enums import ActuatorKind, SensorKind, SystemRole
from melos.core.common.enums import JointKind


class FakeMatrix:
    def copy(self):
        return self

    def to_translation(self):
        return (0.0, 0.0, 0.0)

    def to_quaternion(self):
        return (1.0, 0.0, 0.0, 0.0)


class FakeObject(dict):
    def __init__(self, name: str, *, object_type: str = "EMPTY") -> None:
        super().__init__()
        self.name = name
        self.type = object_type
        self.parent: FakeObject | None = None
        self.children: list[FakeObject] = []
        self.matrix_local = FakeMatrix()
        self.matrix_world = FakeMatrix()

    def get(self, key, default=None):
        return super().get(key, default)


class FakeSettings:
    device_id = "prosthetic"
    device_name = "Prosthetic Leg"
    device_root_link_id = "shank"


class FakeScene:
    def __init__(self, objects: list[FakeObject]) -> None:
        self.objects = objects
        self.melos_blender = FakeSettings()


def test_build_device_from_scene_returns_device_system_model() -> None:
    link = FakeObject("shank_link")
    link["melos_entity_kind"] = "device_link"
    link["melos_id"] = "shank"
    link["melos_name"] = "Shank"

    frame = FakeObject("ankle_frame")
    frame["melos_entity_kind"] = "device_frame"
    frame["melos_id"] = "ankle_frame"
    frame["melos_name"] = "Ankle Frame"
    frame["melos_device_frame_link_id"] = "shank"

    joint = FakeObject("ankle_joint")
    joint["melos_entity_kind"] = "device_joint"
    joint["melos_id"] = "ankle_joint"
    joint["melos_name"] = "Ankle Joint"
    joint["melos_device_joint_kind"] = "revolute"
    joint["melos_device_joint_parent_link_id"] = "shank"
    joint["melos_device_joint_child_link_id"] = "foot"
    joint["melos_device_joint_parent_frame_id"] = "ankle_frame"
    joint["melos_coordinate_id"] = "ankle_flexion"
    joint["melos_coordinate_name"] = "Ankle Flexion"
    joint["melos_coordinate_kind"] = "rotation"
    joint["melos_coordinate_axis"] = (1.0, 0.0, 0.0)

    sensor = FakeObject("shank_imu")
    sensor["melos_entity_kind"] = "device_sensor"
    sensor["melos_id"] = "shank_imu"
    sensor["melos_name"] = "Shank IMU"
    sensor["melos_device_sensor_kind"] = "imu"
    sensor["melos_device_sensor_frame_id"] = "ankle_frame"
    sensor["melos_device_sensor_link_id"] = "shank"

    actuator = FakeObject("ankle_motor")
    actuator["melos_entity_kind"] = "device_actuator"
    actuator["melos_id"] = "ankle_motor"
    actuator["melos_name"] = "Ankle Motor"
    actuator["melos_device_actuator_kind"] = "motor"
    actuator["melos_device_actuator_joint_id"] = "ankle_joint"
    actuator["melos_device_actuator_coordinate_id"] = "ankle_flexion"

    interface = FakeObject("thigh_cuff")
    interface["melos_entity_kind"] = "device_interface"
    interface["melos_id"] = "thigh_cuff"
    interface["melos_name"] = "Thigh Cuff"
    interface["melos_device_interface_kind"] = "cuff"
    interface["melos_device_interface_frame_id"] = "ankle_frame"

    system = build_device_from_scene(FakeScene([link, frame, joint, sensor, actuator, interface]), FakeSettings())

    assert system.role is SystemRole.DEVICE
    assert system.id == "prosthetic"
    assert system.name == "Prosthetic Leg"
    assert system.root_link_id == "shank"
    assert system.links[0].id == "shank"
    assert system.sites[0].id == "ankle_frame"
    assert system.joints[0].kind == JointKind.REVOLUTE
    assert system.joints[0].parent_site_id == "ankle_frame"
    assert system.sensors[0].kind == SensorKind.IMU
    assert system.sensors[0].site_id == "ankle_frame"
    assert system.actuators[0].kind == ActuatorKind.MOTOR
    assert system.actuators[0].joint_id == "ankle_joint"
    interface_site = next(site for site in system.sites if site.id == "thigh_cuff")
    assert "interface" in interface_site.tags
    assert interface_site.parent_site_id == "ankle_frame"


def test_build_device_from_scene_empty() -> None:
    system = build_device_from_scene(FakeScene([]), FakeSettings())

    assert system.role is SystemRole.DEVICE
    assert system.links == []
    assert system.sites == []
    assert system.joints == []
    assert system.sensors == []
    assert system.actuators == []

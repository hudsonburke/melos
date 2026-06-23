from __future__ import annotations

import pytest

from melos.blender.bpy_io.assembly import build_assembly_from_scene
from melos.core.project.model import SystemAssembly


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
        self.parent = None
        self.children: list[FakeObject] = []
        self.matrix_local = FakeMatrix()
        self.matrix_world = FakeMatrix()

    def get(self, key, default=None):
        return super().get(key, default)


class FakeSettings:
    assembly_id = "assembly"
    assembly_name = "assembly"
    anatomical_system_id = "anatomical"


class FakeScene:
    def __init__(self, objects: list[FakeObject]) -> None:
        self.objects = objects
        self.melos_blender = FakeSettings()


def test_build_connection_from_tagged_object() -> None:
    obj = FakeObject("wrist_attachment")
    obj["melos_entity_kind"] = "attachment"
    obj["melos_id"] = "wrist_attach"
    obj["melos_name"] = "Wrist Attachment"
    obj["melos_attachment_device_id"] = "brace"
    obj["melos_attachment_interface_id"] = "wrist_interface"
    obj["melos_attachment_anatomical_site_id"] = "wrist_frame"

    scene = FakeScene([obj])
    assembly = build_assembly_from_scene(scene, FakeSettings())

    assert len(assembly.connections) == 1
    connection = assembly.connections[0]
    assert connection.id == "wrist_attach"
    assert connection.name == "Wrist Attachment"
    assert connection.endpoint_a.system_id == "brace"
    assert connection.endpoint_a.reference_site_ids == ["wrist_interface"]
    assert connection.endpoint_b is not None
    assert connection.endpoint_b.system_id == "anatomical"
    assert connection.endpoint_b.reference_site_ids == ["wrist_frame"]


def test_build_assembly_from_scene_with_connections() -> None:
    obj_a = FakeObject("attach_a")
    obj_a["melos_entity_kind"] = "attachment"
    obj_a["melos_id"] = "attach_a"
    obj_a["melos_name"] = "Attachment A"
    obj_a["melos_attachment_device_id"] = "device_1"
    obj_a["melos_attachment_interface_id"] = "interface_1"

    obj_b = FakeObject("attach_b")
    obj_b["melos_entity_kind"] = "attachment"
    obj_b["melos_id"] = "attach_b"
    obj_b["melos_name"] = "Attachment B"
    obj_b["melos_attachment_device_id"] = "device_2"
    obj_b["melos_attachment_interface_id"] = "interface_2"

    scene = FakeScene([obj_a, obj_b])
    assembly = build_assembly_from_scene(scene, FakeSettings())

    assert isinstance(assembly, SystemAssembly)
    assert len(assembly.connections) == 2
    ids = {connection.id for connection in assembly.connections}
    assert ids == {"attach_a", "attach_b"}


def test_build_assembly_from_scene_empty() -> None:
    scene = FakeScene([])
    assembly = build_assembly_from_scene(scene, FakeSettings())

    assert isinstance(assembly, SystemAssembly)
    assert assembly.connections == []


def test_connection_includes_transform() -> None:
    class CustomMatrix:
        def copy(self):
            return self

        def to_translation(self):
            return (1.0, 2.0, 3.0)

        def to_quaternion(self):
            return (0.707, 0.707, 0.0, 0.0)

    obj = FakeObject("attach_transform")
    obj["melos_entity_kind"] = "attachment"
    obj["melos_id"] = "attach_t"
    obj["melos_name"] = "Transform Attachment"
    obj["melos_attachment_device_id"] = "dev"
    obj["melos_attachment_interface_id"] = "iface"
    obj.matrix_local = CustomMatrix()

    scene = FakeScene([obj])
    assembly = build_assembly_from_scene(scene, FakeSettings())

    connection = assembly.connections[0]
    t = connection.relative_transform
    assert t.translation == (1.0, 2.0, 3.0)
    assert t.rotation[0] == pytest.approx(0.707, abs=1e-6)
    assert t.rotation[1] == pytest.approx(0.707, abs=1e-6)

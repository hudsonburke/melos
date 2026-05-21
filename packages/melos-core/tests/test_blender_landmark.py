from __future__ import annotations

import pytest

from melos.blender.bpy_io.landmark import build_landmarks_from_scene


class FakeMatrix:
    def copy(self):
        return self

    def to_translation(self):
        return (0.0, 0.0, 0.0)

    def to_quaternion(self):
        return (1.0, 0.0, 0.0, 0.0)


class FakeMatrixWithPosition:
    def __init__(self, x: float, y: float, z: float) -> None:
        self._pos = (x, y, z)

    def copy(self):
        return self

    def to_translation(self):
        return self._pos

    def to_quaternion(self):
        return (1.0, 0.0, 0.0, 0.0)


class FakeObject(dict):
    def __init__(self, name: str, *, object_type: str = "EMPTY") -> None:
        super().__init__()
        self.name = name
        self.type = object_type
        self.parent = None
        self.children: list = []
        self.matrix_local = FakeMatrix()
        self.matrix_world = FakeMatrix()

    def get(self, key, default=None):
        return super().get(key, default)


class FakeScene:
    def __init__(self, objects: list) -> None:
        self.objects = objects


def test_build_landmark_from_tagged_object() -> None:
    obj = FakeObject("acromion")
    obj["melos_entity_kind"] = "landmark"
    obj["melos_id"] = "acromion_left"
    obj["melos_name"] = "Left Acromion"
    obj["melos_landmark_body_id"] = "scapula_left"
    obj["melos_landmark_frame_id"] = "scapula_frame"

    scene = FakeScene([obj])
    landmarks = build_landmarks_from_scene(scene)

    assert len(landmarks) == 1
    lm = landmarks[0]
    assert lm.id == "acromion_left"
    assert lm.name == "Left Acromion"
    assert lm.link_id == "scapula_left"
    assert lm.parent_site_id == "scapula_frame"
    assert "landmark" in lm.tags


def test_build_landmarks_from_scene() -> None:
    names = ["ASIS_left", "ASIS_right", "PSIS_left"]
    objects = []
    for i, name in enumerate(names):
        obj = FakeObject(name)
        obj["melos_entity_kind"] = "landmark"
        obj["melos_id"] = name
        obj["melos_name"] = name
        objects.append(obj)

    scene = FakeScene(objects)
    landmarks = build_landmarks_from_scene(scene)

    assert len(landmarks) == 3
    ids = {lm.id for lm in landmarks}
    assert ids == {"ASIS_left", "ASIS_right", "PSIS_left"}


def test_build_landmarks_from_scene_empty() -> None:
    body_obj = FakeObject("pelvis")
    body_obj["melos_entity_kind"] = "anatomical_link"
    body_obj["melos_id"] = "pelvis"

    scene = FakeScene([body_obj])
    landmarks = build_landmarks_from_scene(scene)

    assert landmarks == []


def test_landmark_position_from_matrix() -> None:
    obj = FakeObject("greater_trochanter")
    obj["melos_entity_kind"] = "landmark"
    obj["melos_id"] = "gt_right"
    obj["melos_name"] = "Greater Trochanter Right"
    obj.matrix_local = FakeMatrixWithPosition(0.1, -0.05, 0.9)

    scene = FakeScene([obj])
    landmarks = build_landmarks_from_scene(scene)

    assert len(landmarks) == 1
    lm = landmarks[0]
    assert lm.transform.translation[0] == pytest.approx(0.1)
    assert lm.transform.translation[1] == pytest.approx(-0.05)
    assert lm.transform.translation[2] == pytest.approx(0.9)


def test_landmark_optional_body_and_frame() -> None:
    obj = FakeObject("medial_epicondyle")
    obj["melos_entity_kind"] = "landmark"
    obj["melos_id"] = "med_epi_left"
    obj["melos_name"] = "Medial Epicondyle Left"

    scene = FakeScene([obj])
    landmarks = build_landmarks_from_scene(scene)

    assert len(landmarks) == 1
    lm = landmarks[0]
    assert lm.link_id is None
    assert lm.parent_site_id is None


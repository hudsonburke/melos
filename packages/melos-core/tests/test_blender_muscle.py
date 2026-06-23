from __future__ import annotations

from melos.blender.bpy_io.muscle import build_muscles_from_scene
from melos.core.muscles.enums import MusclePathPointKind, WrapGeometryKind


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
    pass


class FakeScene:
    def __init__(self, objects: list[FakeObject]) -> None:
        self.objects = objects
        self.melos_blender = FakeSettings()


def _make_path_point(name: str, muscle_id: str, order: float, kind: str = MusclePathPointKind.VIA.value) -> FakeObject:
    obj = FakeObject(name)
    obj["melos_entity_kind"] = "muscle_path_point"
    obj["melos_muscle_id"] = muscle_id
    obj["melos_muscle_pp_kind"] = kind
    obj["melos_muscle_pp_order"] = order
    obj["melos_muscle_pp_link_id"] = "pelvis"
    obj["melos_muscle_pp_site_id"] = ""
    return obj


def _make_wrap_geometry(name: str, muscle_id: str) -> FakeObject:
    obj = FakeObject(name)
    obj["melos_entity_kind"] = "muscle_wrap_geometry"
    obj["melos_muscle_id"] = muscle_id
    obj["melos_wrap_kind"] = WrapGeometryKind.CYLINDER.value
    obj["melos_wrap_link_id"] = "femur"
    obj["melos_wrap_site_id"] = ""
    obj["melos_wrap_radius"] = 0.02
    obj["melos_wrap_height"] = 0.1
    return obj


def test_build_muscle_path_point_from_tagged_object() -> None:
    point = _make_path_point("origin_pt", "glut_max", 0.0, kind=MusclePathPointKind.ORIGIN.value)
    scene = FakeScene([point])
    muscles = build_muscles_from_scene(scene, FakeSettings())

    assert len(muscles) == 1
    assert muscles[0].id == "glut_max"
    assert len(muscles[0].path.points) == 1
    pp = muscles[0].path.points[0]
    assert pp.kind == MusclePathPointKind.ORIGIN
    assert pp.link_id == "pelvis"
    assert pp.position == (0.0, 0.0, 0.0)


def test_build_wrap_geometry_from_tagged_object() -> None:
    wrap = _make_wrap_geometry("wrap_cyl", "glut_max")
    scene = FakeScene([wrap])
    muscles = build_muscles_from_scene(scene, FakeSettings())

    assert len(muscles) == 1
    assert len(muscles[0].path.wrap_geometry_ids) == 1
    assert muscles[0].path.wrap_geometry_ids[0] is not None


def test_build_muscles_from_scene_groups_by_muscle_id() -> None:
    p1 = _make_path_point("p1", "muscle_a", 0.0)
    p2 = _make_path_point("p2", "muscle_a", 1.0)
    p3 = _make_path_point("p3", "muscle_b", 0.0)
    scene = FakeScene([p1, p2, p3])
    muscles = build_muscles_from_scene(scene, FakeSettings())

    muscle_ids = {m.id for m in muscles}
    assert muscle_ids == {"muscle_a", "muscle_b"}

    muscle_a = next(m for m in muscles if m.id == "muscle_a")
    assert len(muscle_a.path.points) == 2

    muscle_b = next(m for m in muscles if m.id == "muscle_b")
    assert len(muscle_b.path.points) == 1


def test_build_muscles_from_scene_orders_by_order_key() -> None:
    p_last = _make_path_point("insertion_pt", "quad", 2.0, kind=MusclePathPointKind.INSERTION.value)
    p_mid = _make_path_point("via_pt", "quad", 1.0, kind=MusclePathPointKind.VIA.value)
    p_first = _make_path_point("origin_pt", "quad", 0.0, kind=MusclePathPointKind.ORIGIN.value)
    scene = FakeScene([p_last, p_mid, p_first])
    muscles = build_muscles_from_scene(scene, FakeSettings())

    assert len(muscles) == 1
    points = muscles[0].path.points
    assert len(points) == 3
    assert points[0].kind == MusclePathPointKind.ORIGIN
    assert points[1].kind == MusclePathPointKind.VIA
    assert points[2].kind == MusclePathPointKind.INSERTION


def test_build_muscles_from_scene_empty() -> None:
    scene = FakeScene([])
    muscles = build_muscles_from_scene(scene, FakeSettings())
    assert muscles == []

from __future__ import annotations

from collections import defaultdict

from melos.core.muscles.enums import MusclePathPointKind, WrapGeometryKind
from melos.core.muscles.model import MuscleModel, MusclePath, MusclePathPoint
from melos.core.muscles.wraps import CylinderWrapParameters, WrapGeometry

from melos.blender.constants import (
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
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
)

from .transforms import transform_from_object


def build_muscles_from_scene(scene: object, settings: object) -> list[MuscleModel]:
    point_objects = list(_iter_scene_objects(scene, MUSCLE_PATH_POINT_KIND))
    wrap_objects = list(_iter_scene_objects(scene, MUSCLE_WRAP_GEOMETRY_KIND))

    points_by_muscle: dict[str, list[object]] = defaultdict(list)
    for obj in point_objects:
        muscle_id = _optional_string(obj, MUSCLE_ID_KEY) or ""
        points_by_muscle[muscle_id].append(obj)

    wraps_by_muscle: dict[str, list[object]] = defaultdict(list)
    for obj in wrap_objects:
        muscle_id = _optional_string(obj, MUSCLE_ID_KEY) or ""
        wraps_by_muscle[muscle_id].append(obj)

    all_muscle_ids = set(points_by_muscle.keys()) | set(wraps_by_muscle.keys())

    muscles: list[MuscleModel] = []
    for muscle_id in sorted(all_muscle_ids):
        raw_points = points_by_muscle.get(muscle_id, [])
        raw_points_sorted = sorted(
            raw_points,
            key=lambda o: float(getattr(o, "get", lambda *_: 0.0)(MUSCLE_PATH_POINT_ORDER_KEY, 0.0)),
        )
        path_points = [_build_path_point(obj, idx) for idx, obj in enumerate(raw_points_sorted)]

        raw_wraps = wraps_by_muscle.get(muscle_id, [])
        wrap_geoms = [_build_wrap_geometry(obj, idx) for idx, obj in enumerate(raw_wraps)]
        wrap_ids = [wrap.id for wrap in wrap_geoms]

        seed_obj = raw_points[0] if raw_points else (raw_wraps[0] if raw_wraps else object())
        muscle_name = _optional_string(seed_obj, MUSCLE_NAME_KEY) or muscle_id or "muscle"

        muscles.append(
            MuscleModel(
                id=muscle_id or f"muscle_{len(muscles)}",
                name=muscle_name,
                path=MusclePath(points=path_points, wrap_geometry_ids=wrap_ids),
            )
        )

    return muscles


def build_wrap_geometries_from_scene(scene: object) -> list[WrapGeometry]:
    wrap_objects = list(_iter_scene_objects(scene, MUSCLE_WRAP_GEOMETRY_KIND))
    return [_build_wrap_geometry(obj, idx) for idx, obj in enumerate(wrap_objects)]


def _build_path_point(obj: object, index: int) -> MusclePathPoint:
    getter = getattr(obj, "get", lambda *_: None)
    raw_kind = getter(MUSCLE_PATH_POINT_KIND_KEY) or MusclePathPointKind.VIA.value
    kind = MusclePathPointKind(str(raw_kind))
    link_id = _optional_string(obj, MUSCLE_PATH_POINT_LINK_ID_KEY)
    site_id = _optional_string(obj, MUSCLE_PATH_POINT_SITE_ID_KEY)
    transform = transform_from_object(obj, use_local=True)
    point_id = _optional_string(obj, ENTITY_ID_KEY) or f"point_{index}"
    name = _optional_string(obj, DISPLAY_NAME_KEY) or getattr(obj, "name", point_id)
    return MusclePathPoint(
        id=point_id,
        name=name,
        kind=kind,
        link_id=link_id,
        site_id=site_id,
        position=transform.translation,
    )


def _build_wrap_geometry(obj: object, index: int) -> WrapGeometry:
    getter = getattr(obj, "get", lambda *_: None)
    raw_kind = getter(MUSCLE_WRAP_KIND_KEY) or WrapGeometryKind.CYLINDER.value
    kind = WrapGeometryKind(str(raw_kind))
    link_id = _optional_string(obj, MUSCLE_WRAP_LINK_ID_KEY)
    site_id = _optional_string(obj, MUSCLE_WRAP_SITE_ID_KEY)
    radius = float(getter(MUSCLE_WRAP_RADIUS_KEY) or 0.01)
    height = float(getter(MUSCLE_WRAP_HEIGHT_KEY) or 0.05)
    wrap_id = _optional_string(obj, ENTITY_ID_KEY) or f"wrap_{index}"
    name = _optional_string(obj, DISPLAY_NAME_KEY) or getattr(obj, "name", wrap_id)
    parameters = CylinderWrapParameters(radius=radius, height=height) if kind == WrapGeometryKind.CYLINDER else None
    return WrapGeometry(
        id=wrap_id,
        name=name,
        kind=kind,
        link_id=link_id,
        site_id=site_id,
        transform=transform_from_object(obj, use_local=True),
        parameters=parameters,
    )


def _iter_scene_objects(scene: object, entity_kind: str) -> list[object]:
    objects = getattr(scene, "objects", None)
    if objects is None:
        raise ValueError("Expected a Blender scene with an 'objects' collection.")
    return [
        obj
        for obj in objects
        if getattr(obj, "get", lambda *_: None)(ENTITY_KIND_KEY) == entity_kind
    ]


def _optional_string(obj: object, key: str) -> str | None:
    value = getattr(obj, "get", lambda *_: None)(key)
    if value in (None, ""):
        return None
    return str(value)

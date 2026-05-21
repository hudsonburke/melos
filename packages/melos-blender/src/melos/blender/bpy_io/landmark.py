from __future__ import annotations

from melos.core.common.types import Transform
from melos.core.system.model import Site

from melos.blender.constants import (
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    LANDMARK_BODY_ID_KEY,
    LANDMARK_FRAME_ID_KEY,
    LANDMARK_KIND,
)


def build_landmarks_from_scene(scene: object) -> list[Site]:
    landmark_objects = _iter_scene_objects(scene, LANDMARK_KIND)
    return [_build_landmark_site_from_object(obj) for obj in landmark_objects]


def _build_landmark_site_from_object(object_: object) -> Site:
    position = _position_from_object(object_)
    return Site(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        link_id=_optional_string(object_, LANDMARK_BODY_ID_KEY),
        parent_site_id=_optional_string(object_, LANDMARK_FRAME_ID_KEY),
        transform=Transform(translation=position),
        tags=["landmark"],
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


def _position_from_object(object_: object) -> tuple[float, float, float]:
    matrix = getattr(object_, "matrix_local", None)
    if matrix is None:
        return (0.0, 0.0, 0.0)
    translation = matrix.to_translation()
    return (float(translation[0]), float(translation[1]), float(translation[2]))


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


__all__ = ["build_landmarks_from_scene"]

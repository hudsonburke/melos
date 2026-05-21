"""Transform extraction helpers for Blender-authored melos entities."""

from __future__ import annotations

from typing import Any, Protocol, cast

from melos.core.common.types import Quat, Transform, Vec3


class _MatrixLike(Protocol):
    def copy(self) -> "_MatrixLike": ...
    def to_translation(self) -> tuple[float, float, float]: ...
    def to_quaternion(self) -> tuple[float, float, float, float]: ...


def transform_from_object(object_: object, *, use_local: bool = True) -> Transform:
    """Return a ``Transform`` from a Blender object-like value."""

    matrix = _get_object_matrix(object_, use_local=use_local)
    raw_translation = matrix.to_translation()
    raw_rotation = matrix.to_quaternion()
    translation: Vec3 = (
        float(raw_translation[0]),
        float(raw_translation[1]),
        float(raw_translation[2]),
    )
    rotation: Quat = (
        float(raw_rotation[0]),
        float(raw_rotation[1]),
        float(raw_rotation[2]),
        float(raw_rotation[3]),
    )
    return Transform(translation=translation, rotation=rotation)


def _get_object_matrix(object_: object, *, use_local: bool) -> _MatrixLike:
    object_like = cast(Any, object_)
    if use_local and hasattr(object_like, "matrix_local"):
        return cast(_MatrixLike, object_like.matrix_local.copy())
    if hasattr(object_like, "matrix_world"):
        return cast(_MatrixLike, object_like.matrix_world.copy())
    raise ValueError("Expected a Blender object with matrix_local or matrix_world.")

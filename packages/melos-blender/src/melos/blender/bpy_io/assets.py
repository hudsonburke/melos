"""Blender scene -> ``melos.core.assets`` mapping."""

from __future__ import annotations

from melos.core.assets.model import AssetLibrary, AssetRecord
from melos.core.common.types import AssetRole

from melos.blender.constants import (
    ASSET_ID_KEY,
    ASSET_NAME_KEY,
    ASSET_ROLE_KEY,
    ASSET_URI_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    ANATOMICAL_LINK_ASSET_KIND,
)


def build_asset_library_from_scene(scene: object) -> AssetLibrary:
    """Build a project asset library from tagged Blender objects."""

    items = [build_asset_record_from_object(object_) for object_ in _iter_asset_objects(scene)]
    return AssetLibrary(items=items)


def build_asset_record_from_object(object_: object) -> AssetRecord:
    """Build an ``AssetRecord`` from a tagged Blender object."""

    asset_id = _required_string(object_, ASSET_ID_KEY)
    asset_name = _optional_string(object_, ASSET_NAME_KEY) or getattr(object_, "name", asset_id)
    asset_role_value = _optional_string(object_, ASSET_ROLE_KEY) or AssetRole.VISUAL.value
    asset_uri = _optional_string(object_, ASSET_URI_KEY) or _default_blender_uri(object_)
    return AssetRecord(
        id=asset_id,
        name=asset_name,
        role=AssetRole(asset_role_value),
        uri=asset_uri,
        media_type=_infer_media_type(object_),
    )


def _iter_asset_objects(scene: object) -> list[object]:
    objects = getattr(scene, "objects", None)
    if objects is None:
        raise ValueError("Expected a Blender scene with an 'objects' collection.")

    return [
        object_
        for object_ in objects
        if getattr(object_, "get", lambda *_: None)(ENTITY_KIND_KEY) == ANATOMICAL_LINK_ASSET_KIND
    ]


def _default_blender_uri(object_: object) -> str:
    return f"blender://object/{getattr(object_, 'name', 'unnamed')}"


def _infer_media_type(object_: object) -> str | None:
    if getattr(object_, "type", None) == "MESH":
        return "application/x-blender-mesh"
    return None


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

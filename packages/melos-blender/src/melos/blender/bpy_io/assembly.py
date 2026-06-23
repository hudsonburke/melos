from __future__ import annotations

from melos.core.common.enums import ConnectionKind, ConstraintPolicy, InterfaceKind
from melos.core.system.model import AssemblyConnection, AssemblyEndpoint, SystemAssembly

from melos.blender.constants import (
    ATTACHMENT_DEVICE_ID_KEY,
    ATTACHMENT_INTERFACE_ID_KEY,
    ATTACHMENT_KIND,
    ATTACHMENT_ANATOMICAL_SITE_ID_KEY,
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
)

from .transforms import transform_from_object


def build_assembly_from_scene(scene: object, settings: object) -> SystemAssembly:
    attachment_objects = _iter_scene_objects(scene, ATTACHMENT_KIND)
    anatomical_system_id = getattr(settings, "anatomical_system_id", "anatomical") or "anatomical"
    connections = [_build_attachment_from_object(obj, anatomical_system_id=anatomical_system_id) for obj in attachment_objects]
    return SystemAssembly(
        id=getattr(settings, "assembly_id", "assembly") or "assembly",
        name=getattr(settings, "assembly_name", "assembly") or "assembly",
        connections=connections,
    )


def _build_attachment_from_object(object_: object, *, anatomical_system_id: str) -> AssemblyConnection:
    device_site_id = _required_string(object_, ATTACHMENT_INTERFACE_ID_KEY)
    anatomical_site_id = _optional_string(object_, ATTACHMENT_ANATOMICAL_SITE_ID_KEY)
    return AssemblyConnection(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        endpoint_a=AssemblyEndpoint(
            system_id=_required_string(object_, ATTACHMENT_DEVICE_ID_KEY),
            kind=InterfaceKind.CUSTOM,
            reference_site_ids=[device_site_id],
            tags=["device_attachment_endpoint"],
        ),
        endpoint_b=AssemblyEndpoint(
            system_id=anatomical_system_id,
            kind=InterfaceKind.CUSTOM,
            reference_site_ids=[anatomical_site_id],
            tags=["anatomical_attachment_endpoint"],
        ) if anatomical_site_id is not None else None,
        relative_transform=transform_from_object(object_, use_local=True),
        connection_kind=ConnectionKind.RIGID,
        constraint_policy=ConstraintPolicy.LOWER_TO_WELD,
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


__all__ = ["build_assembly_from_scene"]

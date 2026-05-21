"""Blender scene -> canonical project assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from melos.core.io.json import save_project

from melos.blender.constants import (
    ATTACHMENT_KIND,
    DEVICE_ACTUATOR_KIND,
    DEVICE_FRAME_KIND,
    DEVICE_INTERFACE_KIND,
    DEVICE_JOINT_KIND,
    DEVICE_LINK_KIND,
    DEVICE_SENSOR_KIND,
    ENTITY_KIND_KEY,
    SCENE_SETTINGS_ATTRIBUTE,
)
from melos.blender.services.builders import (
    assemble_project,
    build_project_meta,
    build_simulation_config,
)

from .assembly import build_assembly_from_scene
from .assets import build_asset_library_from_scene
from .device import build_device_from_scene
from .anatomical import build_anatomical_system_from_scene

_DEVICE_ENTITY_KINDS = {
    DEVICE_LINK_KIND,
    DEVICE_FRAME_KIND,
    DEVICE_JOINT_KIND,
    DEVICE_SENSOR_KIND,
    DEVICE_ACTUATOR_KIND,
    DEVICE_INTERFACE_KIND,
}


def build_project_from_scene(scene: object):
    """Build a ``Project`` directly from Blender scene state."""

    settings = getattr(scene, SCENE_SETTINGS_ATTRIBUTE, None)
    if settings is None:
        raise ValueError(
            f"Expected Blender scene to expose '{SCENE_SETTINGS_ATTRIBUTE}' settings."
        )

    meta = build_project_meta(
        project_id=getattr(settings, "project_id", "project"),
        name=getattr(settings, "project_name", "untitled"),
        description=getattr(settings, "project_description", ""),
        created_by=getattr(settings, "created_by", None) or None,
    )
    simulation = build_simulation_config(
        time_step=float(getattr(settings, "time_step", 0.001)),
        duration=_optional_float(getattr(settings, "duration", 0.0)),
        gravity=(
            float(getattr(settings, "gravity_x", 0.0)),
            float(getattr(settings, "gravity_y", 0.0)),
            float(getattr(settings, "gravity_z", -9.81)),
        ),
    )
    assets = build_asset_library_from_scene(scene)

    systems = [build_anatomical_system_from_scene(scene, settings)]
    if _scene_has_any_entity_kind(scene, _DEVICE_ENTITY_KINDS):
        systems.append(build_device_from_scene(scene, settings))

    assemblies = []
    if _scene_has_any_entity_kind(scene, {ATTACHMENT_KIND}):
        assemblies.append(build_assembly_from_scene(scene, settings))

    return assemble_project(
        meta=meta,
        assets=assets,
        systems=systems,
        assemblies=assemblies,
        simulation=simulation,
    )


def save_project_from_scene(scene: object, path: str | Path):
    """Build and save the current Blender-authored project as JSON."""

    project = build_project_from_scene(scene)
    save_project(project, path)
    return project


def _scene_has_any_entity_kind(scene: object, entity_kinds: set[str]) -> bool:
    objects = getattr(scene, "objects", None)
    if objects is None:
        return False
    return any(
        getattr(object_, "get", lambda *_: None)(ENTITY_KIND_KEY) in entity_kinds
        for object_ in objects
    )


def _optional_float(value: object) -> float | None:
    numeric = float(cast_numeric(value))
    if numeric <= 0.0:
        return None
    return numeric


def cast_numeric(value: object) -> float | int | str:
    typed_value = value
    if isinstance(typed_value, (float, int, str)):
        return typed_value
    if hasattr(typed_value, "__float__"):
        return float(cast(Any, typed_value))
    raise ValueError(f"Expected numeric value, received {type(value).__name__}.")

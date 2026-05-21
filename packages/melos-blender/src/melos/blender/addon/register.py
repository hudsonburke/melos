"""Registration helpers for the melos Blender add-on."""

from __future__ import annotations

import importlib

from melos.blender.constants import SCENE_SETTINGS_ATTRIBUTE

from . import properties
from .operators import CLASSES as OPERATOR_CLASSES
from .panels import CLASSES as PANEL_CLASSES


try:
    bpy = importlib.import_module("bpy")
    bpy_props = importlib.import_module("bpy.props")
except ModuleNotFoundError:
    bpy = None
    bpy_props = None


CLASSES = properties.CLASSES + OPERATOR_CLASSES + PANEL_CLASSES


def register() -> None:
    """Register the Blender-facing melos add-on classes."""

    if bpy is None or bpy_props is None:  # pragma: no cover - Blender-only path
        raise RuntimeError("The melos add-on can only be registered inside Blender.")

    for class_ in CLASSES:
        bpy.utils.register_class(class_)

    bpy.types.Scene.melos_blender = bpy_props.PointerProperty(type=properties.MELOSAddonSettings)


def unregister() -> None:
    """Unregister the Blender-facing melos add-on classes."""

    if bpy is None:  # pragma: no cover - Blender-only path
        return

    if hasattr(bpy.types.Scene, SCENE_SETTINGS_ATTRIBUTE):
        del bpy.types.Scene.melos_blender

    for class_ in reversed(CLASSES):
        bpy.utils.unregister_class(class_)


__all__ = ["CLASSES", "register", "unregister"]

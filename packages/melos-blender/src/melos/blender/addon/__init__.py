"""Blender add-on entrypoint for melos authoring tools."""

from melos.blender.constants import BLENDER_SUPPORTED_MAJOR_MINOR

from .register import register, unregister

bl_info = {
    "name": "melos",
    "author": "OpenCode",
    "description": "Author canonical melos core models inside Blender.",
    "blender": (*BLENDER_SUPPORTED_MAJOR_MINOR, 0),
    "version": (0, 1, 0),
    "location": "View3D > Sidebar > melos",
    "category": "Animation",
}

__all__ = ["bl_info", "register", "unregister"]

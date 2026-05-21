"""Blender authoring frontend for canonical melos core models."""

from .services.builders import (
    assemble_project,
    build_project_meta,
    build_simulation_config,
    build_system_model,
)
from .services.ids import allocate_identifier, make_identifier
from .services.validation import format_validation_report

__version__ = "0.1.0"

__all__ = [
    "allocate_identifier",
    "assemble_project",
    "build_project_meta",
    "build_simulation_config",
    "build_system_model",
    "format_validation_report",
    "make_identifier",
]

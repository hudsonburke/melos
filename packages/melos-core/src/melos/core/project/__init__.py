"""Top-level project aggregate models for melos core."""

from __future__ import annotations

from .model import (
    Project,
    ProjectMeta,
    SystemAssembly,
    AssemblyConnection,
    AssemblyEndpoint,
)
from .enums import InterfaceKind, ConnectionKind
from .simulation import SimulationConfig
from .control import ControlInterface, ObservationChannel, CommandChannel
from .assets import AssetRecord, AssetLibrary

__all__ = [
    "Project",
    "ProjectMeta",
    "SystemAssembly",
    "AssemblyConnection",
    "AssemblyEndpoint",
    "InterfaceKind",
    "ConnectionKind",
    "SimulationConfig",
    "ControlInterface",
    "ObservationChannel",
    "CommandChannel",
    "AssetRecord",
    "AssetLibrary",
]

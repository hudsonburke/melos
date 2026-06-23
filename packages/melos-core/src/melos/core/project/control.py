"""Control interface and signal models for project-level contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from melos.core.common.ids import Identifier
from melos.core.common.types import AnnotationMap


@dataclass(slots=True, kw_only=True)
class ObservationChannel:
    """Named observation exposed to controllers or analysis tools."""

    id: Identifier
    name: str
    source_ref: str
    unit: str = ""
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class CommandChannel:
    """Named command accepted by the simulated or physical system."""

    id: Identifier
    name: str
    target_ref: str
    unit: str = ""
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class ControlInterface:
    """Stable control and analysis contract for a project."""

    id: str = "control"
    name: str = "control"
    observations: list[ObservationChannel] = field(default_factory=list)
    commands: list[CommandChannel] = field(default_factory=list)
    annotations: AnnotationMap = field(default_factory=dict)

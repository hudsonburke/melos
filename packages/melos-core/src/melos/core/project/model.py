"""Top-level project model definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from melos.core.project.assets import AssetLibrary
from melos.core.common.ids import Identifier
from melos.core.common.types import AnnotationMap, Transform
from melos.core.project.control import ControlInterface
from melos.core.io.schema import CURRENT_SCHEMA_VERSION
from melos.core.project.attachment import Attachment
from melos.core.project.simulation import SimulationConfig
from melos.core.retarget.translation import TranslationMap
from melos.core.system.model import CoordinateCoupling, SystemModel
from melos.core.project.enums import ConnectionKind, ConstraintPolicy, InterfaceKind


@dataclass(slots=True, kw_only=True)
class AssemblyEndpoint:
    """Contextual attachment endpoint referencing one system's native primitives."""

    system_id: Identifier
    kind: InterfaceKind = InterfaceKind.CUSTOM
    anchor_link_id: Identifier | None = None
    reference_link_ids: list[Identifier] = field(default_factory=list)
    reference_site_ids: list[Identifier] = field(default_factory=list)
    reference_geometry_ids: list[Identifier] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class AssemblyConnection:
    """Connection between one or two contextual assembly endpoints."""

    id: Identifier
    name: str
    endpoint_a: AssemblyEndpoint
    endpoint_b: AssemblyEndpoint | None = None
    relative_transform: Transform = field(default_factory=Transform.identity)
    connection_kind: ConnectionKind = ConnectionKind.RIGID
    constraint_policy: ConstraintPolicy | None = None
    description: str = ""
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class SystemAssembly:
    """Interface-centric assembly connecting one or more systems."""

    id: Identifier = "assembly"
    name: str = "assembly"
    connections: list[AssemblyConnection] = field(default_factory=list)
    couplings: list[CoordinateCoupling] = field(default_factory=list)
    annotations: AnnotationMap = field(default_factory=dict)

 
@dataclass(slots=True, kw_only=True)
class ProjectMeta:
    """Descriptive metadata for a melos project."""

    id: Identifier = "project"
    name: str = "untitled"
    description: str = ""
    created_by: str | None = None
    created_at: str | None = None
    annotations: AnnotationMap = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class Project:
    """Canonical project aggregate shared across frontends and backends."""

    schema_version: str = CURRENT_SCHEMA_VERSION
    meta: ProjectMeta = field(default_factory=ProjectMeta)
    assets: AssetLibrary = field(default_factory=AssetLibrary)
    systems: list[SystemModel] = field(default_factory=list)
    assemblies: list[SystemAssembly] = field(default_factory=list)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    control: ControlInterface = field(default_factory=ControlInterface)
    translation_maps: list[TranslationMap] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary representation of the project."""

        return asdict(self)

    def get_system(self, system_id: Identifier) -> SystemModel | None:
        """Return the system with ``system_id`` if present."""

        return next((system for system in self.systems if system.id == system_id), None)

    def get_systems_by_role(self, role: str) -> list[SystemModel]:
        """Return all systems whose role matches ``role``."""

        return [system for system in self.systems if system.role == role]

    def get_primary_system_by_role(self, role: str) -> SystemModel | None:
        """Return the first system whose role matches ``role`` if present."""

        return next((system for system in self.systems if system.role == role), None)

    def get_anatomical_system(self) -> SystemModel | None:
        """Return the primary anatomical system if present."""

        return self.get_primary_system_by_role("anatomical")


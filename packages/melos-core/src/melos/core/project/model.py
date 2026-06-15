"""Top-level project model definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from melos.core.assets.model import AssetLibrary
from melos.core.common.ids import Identifier
from melos.core.common.metadata import AnnotationMap
from melos.core.control.model import ControlInterface
from melos.core.io.schema import CURRENT_SCHEMA_VERSION
from melos.core.project.skin import SkinAttachment
from melos.core.simulation.model import SimulationConfig
from melos.core.retarget.translation import TranslationMap
from melos.core.system.model import SystemAssembly, SystemModel


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
    skin_attachments: list[SkinAttachment] = field(default_factory=list)

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


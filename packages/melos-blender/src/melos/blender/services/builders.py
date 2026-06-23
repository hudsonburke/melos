"""Pure builders that compose canonical ``melos.core`` models."""

from __future__ import annotations

from melos.core.project.assets import AssetLibrary
from melos.core.project.control import ControlInterface
from melos.core.project.model import Project, ProjectMeta
from melos.core.project.simulation import SimulationConfig
from melos.core.system.enums import SystemRole
from melos.core.project.model import Project, ProjectMeta, SystemAssembly
from melos.core.system.model import (
    Actuator,
    Geometry,
    Joint,
    Link,
    Sensor,
    Site,
    SystemModel,
)


def build_project_meta(
    *,
    project_id: str,
    name: str,
    description: str = "",
    created_by: str | None = None,
    created_at: str | None = None,
) -> ProjectMeta:
    """Build project metadata from UI or scene values."""

    return ProjectMeta(
        id=project_id,
        name=name,
        description=description,
        created_by=created_by,
        created_at=created_at,
    )


def build_simulation_config(
    *,
    time_step: float = 0.001,
    duration: float | None = None,
    gravity: tuple[float, float, float] = (0.0, 0.0, -9.81),
    compile_target: str = "mujoco",
) -> SimulationConfig:
    """Build thin backend-facing simulation preferences."""

    return SimulationConfig(
        compile_target=compile_target,
        time_step=time_step,
        duration=duration,
        gravity=gravity,
    )


def build_system_model(
    *,
    system_id: str,
    name: str,
    role: SystemRole,
    description: str = "",
    links: list[Link] | None = None,
    joints: list[Joint] | None = None,
    sites: list[Site] | None = None,
    geometries: list[Geometry] | None = None,
    actuators: list[Actuator] | None = None,
    sensors: list[Sensor] | None = None,
    root_link_id: str | None = None,
) -> SystemModel:
    """Build a shared articulated system from already-instantiated entities."""

    system_links = list(links or [])
    if root_link_id is None and system_links:
        root_link_id = system_links[0].id

    return SystemModel(
        id=system_id,
        name=name,
        role=role,
        description=description,
        root_link_id=root_link_id,
        links=system_links,
        joints=list(joints or []),
        sites=list(sites or []),
        geometries=list(geometries or []),
        actuators=list(actuators or []),
        sensors=list(sensors or []),
    )


def assemble_project(
    *,
    meta: ProjectMeta,
    systems: list[SystemModel] | None = None,
    assemblies: list[SystemAssembly] | None = None,
    simulation: SimulationConfig | None = None,
    assets: AssetLibrary | None = None,
    control: ControlInterface | None = None,
) -> Project:
    """Assemble a complete canonical project aggregate."""

    return Project(
        meta=meta,
        systems=list(systems or []),
        assemblies=list(assemblies or []),
        simulation=simulation or SimulationConfig(),
        assets=assets or AssetLibrary(),
        control=control or ControlInterface(),
    )

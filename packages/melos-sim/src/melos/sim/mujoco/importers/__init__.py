"""MJCF importer subpackage for ``melos.sim.mujoco``."""

from __future__ import annotations

from pathlib import Path

from melos.core.project.model import Project, ProjectMeta
from melos.core.common.enums import SystemRole
from melos.core.system.model import SystemModel

from .report import ImportReport, ImportResult


def import_mjcf(
    path: str | Path,
    *,
    output_dir: str | Path | None = None,
    project_id: str | None = None,
) -> ImportResult:
    """Import an MJCF file into a :class:`~melos.core.project.model.Project`."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MJCF file not found: {path}")

    output_dir_path: Path | None = Path(output_dir) if output_dir is not None else None
    report = ImportReport()

    from .assets import map_assets
    from .bodies import map_bodies
    from .config import map_simulation_config
    from .defaults import resolve_defaults
    from .joints import map_joints
    from .muscles import map_muscle_paths, map_muscle_physiology, map_sites
    from .wraps import map_wrap_geometries
    from .xml_parser import parse_mjcf_file

    root, directives, report = parse_mjcf_file(path, report)
    defaults = resolve_defaults(root)

    worldbody = root.find("worldbody")
    if worldbody is None:
        report.add_warning(
            code="MISSING_WORLDBODY",
            message="MJCF has no <worldbody> element",
            location=str(path),
        )
        worldbody_el = root
    else:
        worldbody_el = worldbody

    links, body_tree = map_bodies(worldbody_el, defaults, report)
    sites = map_sites(worldbody_el, report)
    joints = map_joints(worldbody_el, body_tree, defaults, directives, report)

    tendon_section = root.find("tendon")
    geometries, wrap_geom_map = map_wrap_geometries(worldbody_el, tendon_section, body_tree, defaults, report)
    actuators = map_muscle_paths(tendon_section, worldbody_el, wrap_geom_map, body_tree, report)

    actuator_section = root.find("actuator")
    if actuator_section is not None:
        physiology_map = map_muscle_physiology(actuator_section, defaults, report)
        for actuator in actuators:
            if actuator.id in physiology_map:
                actuator.parameters = {
                    **actuator.parameters,
                    "physiology": physiology_map[actuator.id],
                }

    assets = map_assets(root, directives, path, output_dir_path, report)
    simulation = map_simulation_config(root, directives, report)

    root_link_id = links[0].id if links else None
    pid = project_id if project_id is not None else path.stem

    anatomical_system = SystemModel(
        id="anatomical",
        name=pid,
        role=SystemRole.ANATOMICAL,
        root_link_id=root_link_id,
        links=links,
        joints=joints,
        sites=sites,
        geometries=geometries,
        actuators=actuators,
    )

    project = Project(
        meta=ProjectMeta(id=pid, name=pid),
        assets=assets,
        systems=[anatomical_system],
        simulation=simulation,
    )

    return ImportResult(project=project, report=report)


__all__ = ["import_mjcf", "ImportResult", "ImportReport"]

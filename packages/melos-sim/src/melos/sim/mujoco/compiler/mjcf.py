"""Minimal MJCF compiler for shared-system melos projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, indent, tostring

from melos.core.assets.model import AssetRecord
from melos.core.common.types import AssetRole, Bounds, InertialProperties, Transform, Vec3
from melos.core.control.model import CommandChannel, ObservationChannel
from melos.core.io.json import load_project
from melos.core.kinematics.model import CoordinateKind, JointKind
from melos.core.project.model import Project
from melos.core.system.enums import ActuatorKind, GeometryRole, RouteNodeKind, SensorKind, SystemRole
from melos.core.system.model import Actuator, Geometry, Joint, Link, Sensor, Site, SystemModel
from melos.core.validation import validate_project

from ..reports import CompileReport, MujocoCompileResult, SignalBinding, SignalMap
from .assets import build_asset_manifest
from .attachments import compose_transforms, resolve_system_root_placement
from .muscles import build_muscle_site_sequence, get_wrap_geom_spec


@dataclass(slots=True)
class _CompilerState:
    report: CompileReport = field(default_factory=CompileReport)
    coordinate_joint_names: dict[str, str] = field(default_factory=dict)
    actuator_names: dict[tuple[str | None, str], str] = field(default_factory=dict)
    body_elements: dict[tuple[str, str], Element] = field(default_factory=dict)
    site_names: dict[tuple[str, str], str] = field(default_factory=dict)
    site_transforms: dict[tuple[str, str], Transform] = field(default_factory=dict)
    joint_names: dict[tuple[str, str], str] = field(default_factory=dict)
    link_joint_names: dict[tuple[str, str], str] = field(default_factory=dict)
    sensor_names: dict[tuple[str, str], str] = field(default_factory=dict)
    wrap_geom_names: dict[tuple[str, str], str] = field(default_factory=dict)
    tendon_names: dict[tuple[str, str], str] = field(default_factory=dict)


def compile_project(
    project: Project,
    *,
    validate: bool = True,
) -> MujocoCompileResult:
    """Compile a melos project into minimal MuJoCo-facing artifacts."""

    if project.simulation.compile_target != "mujoco":
        raise ValueError(
            "melos.sim.mujoco can only compile projects whose compile_target is 'mujoco'."
        )

    state = _CompilerState()
    if validate:
        validation_report = validate_project(project)
        if validation_report.has_errors:
            raise ValueError(
                "Cannot compile project with validation errors: "
                f"{validation_report.issues}"
            )

    root = Element("mujoco", {"model": project.meta.id})
    option_attrs = {
        "timestep": _format_scalar(project.simulation.time_step),
        "gravity": _format_vec3(project.simulation.gravity),
        "integrator": project.simulation.integrator.value,
        "solver": project.simulation.solver_type.value,
        "iterations": str(project.simulation.solver_iterations),
        "tolerance": _format_scalar(project.simulation.solver_tolerance),
    }
    if project.simulation.noslip_iterations > 0:
        option_attrs["noslip_iterations"] = str(project.simulation.noslip_iterations)
    SubElement(root, "option", option_attrs)
    SubElement(root, "compiler", {"angle": "radian", "balanceinertia": "true", "boundmass": "0.001", "boundinertia": "0.0001"})

    asset_lookup: dict[str, AssetRecord] = {asset.id: asset for asset in project.assets.items}
    _append_asset_section(root, project, asset_lookup, state)

    worldbody = SubElement(root, "worldbody")
    tendon = SubElement(root, "tendon")
    actuator = SubElement(root, "actuator")
    sensor = SubElement(root, "sensor")

    SubElement(
        worldbody,
        "geom",
        {
            "name": "ground",
            "type": "plane",
            "size": "5 5 0.1",
            "rgba": "0.8 0.8 0.8 1",
            "conaffinity": "1",
            "condim": "3",
        },
    )

    for system in project.systems:
        _append_system(worldbody, project, system, asset_lookup, state)

    _append_routed_tendons(tendon, project, state)
    _append_system_actuators(actuator, project, state)
    _append_tendon_actuators(actuator, project, state)
    _append_system_sensors(sensor, project, state)
    signal_map = _build_signal_map(sensor, project, state)

    for section in (tendon, actuator, sensor):
        if len(section) == 0:
            root.remove(section)

    if project.simulation.keyframes:
        keyframe_section = SubElement(root, "keyframe")
        for keyframe_name, keyframe_values in project.simulation.keyframes.items():
            qpos_parts: list[str] = []
            for coordinate_id in state.coordinate_joint_names:
                qpos_parts.append(_format_scalar(keyframe_values.get(coordinate_id, 0.0)))
            if qpos_parts:
                SubElement(
                    keyframe_section,
                    "key",
                    {"name": keyframe_name, "qpos": " ".join(qpos_parts)},
                )

    indent(root, space="  ")
    return MujocoCompileResult(
        mjcf_text=tostring(root, encoding="unicode"),
        asset_manifest=build_asset_manifest(project),
        signal_map=signal_map,
        report=state.report,
    )


def compile_project_file(
    path: str | Path,
    *,
    validate: bool = True,
) -> MujocoCompileResult:
    """Load a JSON project file and compile it to MuJoCo artifacts."""

    return compile_project(load_project(path), validate=validate)


def _append_asset_section(
    root: Element,
    project: Project,
    asset_lookup: dict[str, AssetRecord],
    state: _CompilerState,
) -> None:
    visual_refs: list[tuple[str, str, str]] = []
    for system in project.systems:
        for link in system.links:
            for asset_id in link.asset_ids:
                visual_refs.append((system.id, link.id, asset_id))

    if not visual_refs:
        return

    asset_section = SubElement(root, "asset")
    for system_id, link_id, asset_id in visual_refs:
        record = asset_lookup.get(asset_id)
        if record is not None and record.role == AssetRole.VISUAL:
            mesh_attrs: dict[str, str] = {"name": asset_id, "file": record.uri}
            scale = record.annotations.get("mjcf_mesh_scale") or record.annotations.get("mjcf_geom_scale")
            if scale is not None:
                mesh_attrs["scale"] = scale
            SubElement(asset_section, "mesh", mesh_attrs)
        else:
            state.report.add_warning(
                code="visual.asset.unresolved",
                message=(
                    f"Link {link_id!r} on system {system_id!r} references asset "
                    f"{asset_id!r} not found as VISUAL in project.assets."
                ),
                location=f"systems[{system_id}].links[{link_id}].asset_ids",
            )

    if len(asset_section) == 0:
        root.remove(asset_section)


def _append_system(
    parent: Element,
    project: Project,
    system: SystemModel,
    asset_lookup: dict[str, AssetRecord],
    state: _CompilerState,
) -> None:
    links_by_id = {link.id: link for link in system.links}
    sites_by_link_id: dict[str, list[Site]] = {}
    for site in system.sites:
        if site.link_id is not None:
            sites_by_link_id.setdefault(site.link_id, []).append(site)
            state.site_transforms[(system.id, site.id)] = site.transform

    geometries_by_link_id: dict[str, list[Geometry]] = {}
    for geometry in system.geometries:
        if geometry.link_id is not None:
            geometries_by_link_id.setdefault(geometry.link_id, []).append(geometry)

    joints_by_parent_id: dict[str | None, list[Joint]] = {}
    for joint in system.joints:
        joints_by_parent_id.setdefault(joint.parent_link_id, []).append(joint)

    if system.root_link_id is None:
        return

    root_link = links_by_id.get(system.root_link_id)
    if root_link is None:
        return

    root_transform = root_link.transform
    if system.role != SystemRole.ANATOMICAL:
        placement = resolve_system_root_placement(project, system, state.report)
        if placement is not None:
            root_transform = compose_transforms(placement.transform, root_transform)

    _append_link(
        parent,
        system=system,
        link=root_link,
        links_by_id=links_by_id,
        sites_by_link_id=sites_by_link_id,
        geometries_by_link_id=geometries_by_link_id,
        joints_by_parent_id=joints_by_parent_id,
        transform_override=root_transform,
        joint_from_parent=None,
        asset_lookup=asset_lookup,
        state=state,
    )


def _append_link(
    parent: Element,
    *,
    system: SystemModel,
    link: Link,
    links_by_id: dict[str, Link],
    sites_by_link_id: dict[str, list[Site]],
    geometries_by_link_id: dict[str, list[Geometry]],
    joints_by_parent_id: dict[str | None, list[Joint]],
    transform_override: Transform | None,
    joint_from_parent: Joint | None,
    asset_lookup: dict[str, AssetRecord],
    state: _CompilerState,
) -> None:
    transform = transform_override or link.transform
    attributes = {"name": _body_name(system.id, link.id)}
    if transform.translation != (0.0, 0.0, 0.0):
        attributes["pos"] = _format_vec3(transform.translation)
    if transform.rotation != (1.0, 0.0, 0.0, 0.0):
        attributes["quat"] = _format_quat(transform.rotation)

    body_element = SubElement(parent, "body", attributes)
    state.body_elements[(system.id, link.id)] = body_element
    _append_inertial(body_element, link.inertial)
    _append_sites(body_element, system.id, sites_by_link_id.get(link.id, []), state)
    _append_geometries(body_element, system, geometries_by_link_id.get(link.id, []), asset_lookup, state)
    _append_visual_geoms(body_element, system.id, link, asset_lookup)

    if joint_from_parent is not None:
        _append_joint(body_element, system.id, joint_from_parent, state)

    for child_joint in joints_by_parent_id.get(link.id, []):
        child_link = links_by_id.get(child_joint.child_link_id)
        if child_link is None:
            continue
        _append_link(
            body_element,
            system=system,
            link=child_link,
            links_by_id=links_by_id,
            sites_by_link_id=sites_by_link_id,
            geometries_by_link_id=geometries_by_link_id,
            joints_by_parent_id=joints_by_parent_id,
            transform_override=None,
            joint_from_parent=child_joint,
            asset_lookup=asset_lookup,
            state=state,
        )


def _append_sites(body_element: Element, system_id: str, sites: list[Site], state: _CompilerState) -> None:
    for site in sites:
        site_name = f"{system_id}_site_{site.id}"
        SubElement(
            body_element,
            "site",
            {
                "name": site_name,
                "pos": _format_vec3(site.transform.translation),
                "quat": _format_quat(site.transform.rotation),
                "size": "0.005",
                "rgba": "0.2 0.5 0.9 0.35",
            },
        )
        state.site_names[(system_id, site.id)] = site_name


def _append_geometries(
    body_element: Element,
    system: SystemModel,
    geometries: list[Geometry],
    asset_lookup: dict[str, AssetRecord],
    state: _CompilerState,
) -> None:
    for geometry in geometries:
        if geometry.role == GeometryRole.WRAP:
            wrap_spec = get_wrap_geom_spec(geometry, state.report)
            if wrap_spec is None:
                continue
            geom_type, size = wrap_spec
            SubElement(
                body_element,
                "geom",
                {
                    "name": f"{system.id}_wrap_{geometry.id}",
                    "type": geom_type,
                    "pos": _format_vec3(geometry.transform.translation),
                    "quat": _format_quat(geometry.transform.rotation),
                    "size": size,
                    "contype": "0",
                    "conaffinity": "0",
                    "rgba": "0.8 0.6 0.2 0.35",
                },
            )
            state.wrap_geom_names[(system.id, geometry.id)] = f"{system.id}_wrap_{geometry.id}"
            continue

        if geometry.role == GeometryRole.CONTACT:
            attributes: dict[str, str] = {
                "name": f"contact_{geometry.id}",
                "type": geometry.kind,
                "pos": _format_vec3(geometry.transform.translation),
                "quat": _format_quat(geometry.transform.rotation),
            }
            size = _geometry_size_string(geometry)
            if size is not None:
                attributes["size"] = size
            if geometry.kind == "mesh" and geometry.asset_id is not None:
                record = asset_lookup.get(geometry.asset_id)
                if record is not None and record.role == AssetRole.VISUAL:
                    attributes["mesh"] = geometry.asset_id
            SubElement(body_element, "geom", attributes)


def _append_visual_geoms(
    body_element: Element,
    system_id: str,
    link: Link,
    asset_lookup: dict[str, AssetRecord],
) -> None:
    for asset_id in link.asset_ids:
        record = asset_lookup.get(asset_id)
        if record is not None and record.role == AssetRole.VISUAL:
            attrs: dict[str, str] = {
                "name": f"visual_{system_id}_{asset_id}",
                "type": "mesh",
                "mesh": asset_id,
                "contype": "0",
                "conaffinity": "0",
                "group": "1",
            }
            pos = record.annotations.get("mjcf_geom_pos")
            if pos is not None:
                attrs["pos"] = pos
            quat = record.annotations.get("mjcf_geom_quat")
            if quat is not None:
                attrs["quat"] = quat
            SubElement(body_element, "geom", attrs)


def _append_joint(body_element: Element, system_id: str, joint: Joint, state: _CompilerState) -> None:
    if joint.kind == JointKind.FIXED:
        return

    if joint.kind == JointKind.FREE:
        name = joint.coordinates[0].id if joint.coordinates else joint.id
        SubElement(body_element, "freejoint", {"name": name})
        if joint.coordinates:
            state.coordinate_joint_names[joint.coordinates[0].id] = name
        state.joint_names[(system_id, joint.id)] = name
        state.link_joint_names[(system_id, joint.child_link_id)] = name
        return

    if joint.kind == JointKind.SPHERICAL:
        name = joint.coordinates[0].id if joint.coordinates else joint.id
        SubElement(body_element, "joint", {"name": name, "type": "ball"})
        if joint.coordinates:
            state.coordinate_joint_names[joint.coordinates[0].id] = name
        state.joint_names[(system_id, joint.id)] = name
        state.link_joint_names[(system_id, joint.child_link_id)] = name
        return

    if joint.kind == JointKind.UNIVERSAL:
        coordinates = joint.coordinates[:2]
        if not coordinates:
            return
        for coordinate in coordinates:
            attributes: dict[str, str] = {
                "name": coordinate.id,
                "type": "hinge",
                "axis": _format_vec3(coordinate.axis),
            }
            _apply_limits_and_reference(attributes, coordinate.limits, coordinate.default_value)
            SubElement(body_element, "joint", attributes)
            state.coordinate_joint_names[coordinate.id] = coordinate.id
        state.joint_names[(system_id, joint.id)] = coordinates[0].id
        state.link_joint_names[(system_id, joint.child_link_id)] = coordinates[0].id
        return

    if joint.kind == JointKind.PLANAR:
        default_axes: list[Vec3] = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
        first_name = None
        for index in range(3):
            if index < len(joint.coordinates):
                coordinate = joint.coordinates[index]
                name = coordinate.id
                axis = coordinate.axis
                joint_type = "slide" if index < 2 else "hinge"
                attributes = {"name": name, "type": joint_type, "axis": _format_vec3(axis)}
                _apply_limits_and_reference(attributes, coordinate.limits, coordinate.default_value)
                SubElement(body_element, "joint", attributes)
                state.coordinate_joint_names[coordinate.id] = name
            else:
                name = f"{joint.id}_planar_{index}"
                joint_type = "slide" if index < 2 else "hinge"
                SubElement(body_element, "joint", {"name": name, "type": joint_type, "axis": _format_vec3(default_axes[index])})
            if first_name is None:
                first_name = name
        if first_name is not None:
            state.joint_names[(system_id, joint.id)] = first_name
            state.link_joint_names[(system_id, joint.child_link_id)] = first_name
        return

    if joint.kind == JointKind.CUSTOM:
        # Compound joint with mixed translation/rotation coordinates.
        # Emit each coordinate as a separate MuJoCo joint element.
        if not joint.coordinates:
            state.report.add_warning(
                code="joint.custom_unsupported",
                message=(
                    f"Joint {joint.id!r} uses custom kind with no coordinates; "
                    "the MuJoCo compiler cannot lower it."
                ),
                location=f"systems[{system_id}].joints[{joint.id}]",
            )
            return
        first_name = None
        for coordinate in joint.coordinates:
            jtype = "slide" if coordinate.kind == CoordinateKind.TRANSLATION else "hinge"
            attributes = {
                "name": coordinate.id,
                "type": jtype,
                "axis": _format_vec3(coordinate.axis),
            }
            _apply_limits_and_reference(attributes, coordinate.limits, coordinate.default_value)
            SubElement(body_element, "joint", attributes)
            state.coordinate_joint_names[coordinate.id] = coordinate.id
            if first_name is None:
                first_name = coordinate.id
        if first_name is not None:
            state.joint_names[(system_id, joint.id)] = first_name
            state.link_joint_names[(system_id, joint.child_link_id)] = first_name
        return

    if not joint.coordinates:
        return
    coordinate = joint.coordinates[0]
    joint_name = coordinate.id
    attributes = {
        "name": joint_name,
        "type": "hinge" if joint.kind == JointKind.REVOLUTE else "slide",
        "axis": _format_vec3(coordinate.axis),
    }
    _apply_limits_and_reference(attributes, coordinate.limits, coordinate.default_value)
    SubElement(body_element, "joint", attributes)
    state.coordinate_joint_names[coordinate.id] = joint_name
    state.joint_names[(system_id, joint.id)] = joint_name
    state.link_joint_names[(system_id, joint.child_link_id)] = joint_name


def _apply_limits_and_reference(
    attributes: dict[str, str],
    limits: Bounds | None,
    default_value: float,
) -> None:
    if limits is not None:
        lower = limits.lower if limits.lower is not None else -1e6
        upper = limits.upper if limits.upper is not None else 1e6
        attributes["limited"] = "true"
        attributes["range"] = _format_scalars(lower, upper)
    if default_value != 0.0:
        attributes["ref"] = _format_scalar(default_value)


def _append_inertial(body_element: Element, inertial: InertialProperties | None) -> None:
    if inertial is None:
        return
    if inertial.mass is None or inertial.center_of_mass is None or inertial.inertia_about_com is None:
        return
    SubElement(
        body_element,
        "inertial",
        {
            "mass": _format_scalar(inertial.mass),
            "pos": _format_vec3(inertial.center_of_mass),
            "fullinertia": _format_inertia6(inertial.inertia_about_com),
        },
    )


def _append_routed_tendons(tendon: Element, project: Project, state: _CompilerState) -> None:
    """Lower MUSCLE and CABLE actuators to spatial tendons routed through sites/wraps."""

    for system in project.systems:
        for actuator in system.actuators:
            if actuator.kind not in (ActuatorKind.MUSCLE, ActuatorKind.CABLE):
                continue
            path_elements, site_count = _resolve_tendon_path(actuator, system.id, state)
            if site_count < 2:
                code = (
                    "muscle.path.unresolved"
                    if actuator.kind == ActuatorKind.MUSCLE
                    else "cable.path.unresolved"
                )
                state.report.add_warning(
                    code=code,
                    message=(
                        f"Actuator {actuator.id!r} did not resolve to at least two MuJoCo "
                        "sites; skipping tendon export."
                    ),
                    location=f"systems[{system.id}].actuators[{actuator.id}]",
                )
                continue
            prefix = "muscle" if actuator.kind == ActuatorKind.MUSCLE else "cable"
            spatial_attrs = {"name": f"{prefix}_{actuator.id}"}
            _apply_cable_spatial_attrs(spatial_attrs, actuator.cable)
            spatial = SubElement(tendon, "spatial", spatial_attrs)
            for tag, attributes in path_elements:
                SubElement(spatial, tag, attributes)
            state.tendon_names[(system.id, actuator.id)] = spatial_attrs["name"]


def _resolve_tendon_path(
    actuator: Actuator,
    system_id: str,
    state: _CompilerState,
) -> tuple[list[tuple[str, dict[str, str]]], int]:
    """Resolve an ordered tendon path, preferring ``route`` over legacy ``site_ids``."""

    def _lookup_site(site_id: str) -> str | None:
        """Look up a site name, first in the owning system then across all systems."""
        name = state.site_names.get((system_id, site_id))
        if name is not None:
            return name
        for key, n in state.site_names.items():
            if key[1] == site_id:
                return n
        return None

    def _lookup_wrap_geom(geometry_id: str) -> str | None:
        name = state.wrap_geom_names.get((system_id, geometry_id))
        if name is not None:
            return name
        for key, n in state.wrap_geom_names.items():
            if key[1] == geometry_id:
                return n
        return None

    elements: list[tuple[str, dict[str, str]]] = []
    site_count = 0
    if actuator.route:
        for index, node in enumerate(actuator.route):
            location = f"systems[{system_id}].actuators[{actuator.id}].route[{index}]"
            if node.kind == RouteNodeKind.WRAP and node.geometry_id is not None:
                geom_name = _lookup_wrap_geom(node.geometry_id)
                if geom_name is None:
                    state.report.add_warning(
                        code="tendon.wrap_unresolved",
                        message=(
                            f"Route wrap geometry {node.geometry_id!r} on actuator "
                            f"{actuator.id!r} is not a compiled wrap geom; skipping waypoint."
                        ),
                        location=location,
                    )
                    continue
                wrap_attrs = {"geom": geom_name}
                if node.side_site_id is not None:
                    side_name = _lookup_site(node.side_site_id)
                    if side_name is not None:
                        wrap_attrs["sidesite"] = side_name
                elements.append(("geom", wrap_attrs))
                continue
            if node.site_id is None:
                continue
            site_name = _lookup_site(node.site_id)
            if site_name is None:
                state.report.add_warning(
                    code="tendon.site_unresolved",
                    message=(
                        f"Route site {node.site_id!r} on actuator {actuator.id!r} did not "
                        "resolve to a MuJoCo site; skipping waypoint."
                    ),
                    location=location,
                )
                continue
            elements.append(("site", {"site": site_name}))
            site_count += 1
        return elements, site_count

    for site_name in build_muscle_site_sequence(actuator, state.site_names, system_id, state.report):
        elements.append(("site", {"site": site_name}))
        site_count += 1
    return elements, site_count


def _apply_cable_spatial_attrs(attributes: dict[str, str], cable: object | None) -> None:
    if cable is None:
        return
    width = getattr(cable, "width", None)
    if width is not None:
        attributes["width"] = _format_scalar(float(width))
    stiffness = getattr(cable, "stiffness", 0.0)
    if stiffness:
        attributes["stiffness"] = _format_scalar(float(stiffness))
    damping = getattr(cable, "damping", 0.0)
    if damping:
        attributes["damping"] = _format_scalar(float(damping))
    rest_length = getattr(cable, "rest_length", None)
    if rest_length is not None:
        attributes["springlength"] = _format_scalar(float(rest_length))
    length_range = getattr(cable, "length_range", None)
    if length_range is not None and length_range.lower is not None and length_range.upper is not None:
        attributes["range"] = _format_scalars(float(length_range.lower), float(length_range.upper))
        attributes["limited"] = "true"


def _append_tendon_actuators(actuator_element: Element, project: Project, state: _CompilerState) -> None:
    """Emit driving actuators for tendon-backed muscles and cables."""

    for system in project.systems:
        for actuator in system.actuators:
            tendon_name = state.tendon_names.get((system.id, actuator.id))
            if tendon_name is None:
                continue
            if actuator.kind == ActuatorKind.MUSCLE:
                backend_name = f"{system.id}_muscle_{actuator.id}"
                attributes = {"name": backend_name, "tendon": tendon_name}
                physiology = actuator.parameters.get("physiology")
                if isinstance(physiology, dict) and "_raw_gainprm" in physiology:
                    # Emit <general> with original attributes for round-trip fidelity.
                    for attr in ("gainprm", "biasprm", "dynprm", "lengthrange"):
                        raw = physiology.get(f"_raw_{attr}")
                        if raw is not None:
                            attributes[attr] = str(raw)
                    force = physiology.get("max_isometric_force")
                    if isinstance(force, (int, float)):
                        attributes["force"] = _format_scalar(float(force))
                    SubElement(actuator_element, "general", attributes)
                else:
                    _apply_muscle_actuator_params(attributes, actuator)
                    SubElement(actuator_element, "muscle", attributes)
            else:
                backend_name = f"{system.id}_actuator_{actuator.id}"
                attributes = {"name": backend_name, "tendon": tendon_name}
                _apply_actuator_bounds(attributes, actuator.command_limits, control=True)
                _apply_actuator_bounds(attributes, actuator.output_limits, control=False)
                SubElement(actuator_element, "motor", attributes)
            state.actuator_names[(system.id, actuator.id)] = backend_name
            state.actuator_names[(None, actuator.id)] = backend_name


def _apply_muscle_actuator_params(attributes: dict[str, str], actuator: Actuator) -> None:
    physiology = actuator.parameters.get("physiology")
    if not isinstance(physiology, dict):
        return
    force = physiology.get("max_isometric_force")
    if isinstance(force, (int, float)):
        attributes["force"] = _format_scalar(float(force))


def _append_system_actuators(actuator_element: Element, project: Project, state: _CompilerState) -> None:
    for system in project.systems:
        if system.role == SystemRole.ANATOMICAL:
            continue
        for actuator in system.actuators:
            if actuator.kind in (ActuatorKind.MUSCLE, ActuatorKind.CABLE):
                continue
            _append_system_actuator(actuator_element, system.id, actuator, state)


def _append_system_actuator(
    actuator_element: Element,
    system_id: str,
    actuator: Actuator,
    state: _CompilerState,
) -> None:
    backend_name = f"{system_id}_actuator_{actuator.id}"
    joint_name = None
    if actuator.coordinate_id is not None:
        joint_name = state.coordinate_joint_names.get(actuator.coordinate_id)
    if joint_name is None and actuator.joint_id is not None:
        joint_name = state.joint_names.get((system_id, actuator.joint_id))

    if joint_name is None:
        state.report.add_warning(
            code="actuator.target_unresolved",
            message=(
                f"Actuator {actuator.id!r} on system {system_id!r} did not resolve to "
                "a MuJoCo joint and was skipped."
            ),
            location=f"systems[{system_id}].actuators[{actuator.id}]",
        )
        return

    element_name = _mujoco_actuator_element_name(actuator.kind)
    attributes = {"name": backend_name, "joint": joint_name}
    _apply_actuator_bounds(attributes, actuator.command_limits, control=True)
    _apply_actuator_bounds(attributes, actuator.output_limits, control=False)
    SubElement(actuator_element, element_name, attributes)
    state.actuator_names[(system_id, actuator.id)] = backend_name
    state.actuator_names[(None, actuator.id)] = backend_name


def _apply_actuator_bounds(attributes: dict[str, str], bounds: Bounds | None, *, control: bool) -> None:
    if bounds is None:
        return
    lower = bounds.lower if bounds.lower is not None else -1e6
    upper = bounds.upper if bounds.upper is not None else 1e6
    if control:
        attributes["ctrllimited"] = "true"
        attributes["ctrlrange"] = _format_scalars(lower, upper)
    else:
        attributes["forcelimited"] = "true"
        attributes["forcerange"] = _format_scalars(lower, upper)


def _append_system_sensors(sensor_element: Element, project: Project, state: _CompilerState) -> None:
    for system in project.systems:
        if system.role == SystemRole.ANATOMICAL:
            continue
        for sensor in system.sensors:
            _append_system_sensor(sensor_element, system.id, sensor, state)


def _append_system_sensor(
    sensor_element: Element,
    system_id: str,
    sensor: Sensor,
    state: _CompilerState,
) -> None:
    backend_name = f"{system_id}_sensor_{sensor.id}"
    site_name = state.site_names.get((system_id, sensor.site_id)) if sensor.site_id is not None else None

    if sensor.kind == SensorKind.POSITION:
        joint_name = _find_joint_for_link(system_id, sensor.link_id, state)
        if joint_name is not None:
            SubElement(sensor_element, "jointpos", {"name": backend_name, "joint": joint_name})
        else:
            state.report.add_warning(
                code="sensor.joint_unresolved",
                message=(
                    f"Sensor {sensor.id!r} on system {system_id!r} (kind=position) "
                    "could not resolve to a joint; skipping."
                ),
                location=f"systems[{system_id}].sensors[{sensor.id}]",
            )
            return
    elif sensor.kind == SensorKind.VELOCITY:
        joint_name = _find_joint_for_link(system_id, sensor.link_id, state)
        if joint_name is not None:
            SubElement(sensor_element, "jointvel", {"name": backend_name, "joint": joint_name})
        else:
            state.report.add_warning(
                code="sensor.joint_unresolved",
                message=(
                    f"Sensor {sensor.id!r} on system {system_id!r} (kind=velocity) "
                    "could not resolve to a joint; skipping."
                ),
                location=f"systems[{system_id}].sensors[{sensor.id}]",
            )
            return
    elif sensor.kind == SensorKind.FORCE:
        if site_name is not None:
            SubElement(sensor_element, "force", {"name": backend_name, "site": site_name})
        else:
            return
    elif sensor.kind == SensorKind.TORQUE:
        if site_name is not None:
            SubElement(sensor_element, "torque", {"name": backend_name, "site": site_name})
        else:
            return
    elif sensor.kind == SensorKind.IMU:
        if site_name is not None:
            SubElement(sensor_element, "accelerometer", {"name": f"{backend_name}_acc", "site": site_name})
            SubElement(sensor_element, "gyro", {"name": f"{backend_name}_gyro", "site": site_name})
        else:
            return
    elif sensor.kind == SensorKind.CONTACT:
        if site_name is not None:
            SubElement(sensor_element, "touch", {"name": backend_name, "site": site_name})
        else:
            return
    else:
        state.report.add_warning(
            code="sensor.unsupported_kind",
            message=f"Sensor {sensor.id!r} on system {system_id!r} uses unsupported kind {sensor.kind!r}.",
            location=f"systems[{system_id}].sensors[{sensor.id}]",
        )
        return

    state.sensor_names[(system_id, sensor.id)] = backend_name


def _find_joint_for_link(system_id: str, link_id: str | None, state: _CompilerState) -> str | None:
    if link_id is None:
        return None
    return state.link_joint_names.get((system_id, link_id))


def _build_signal_map(sensor_element: Element, project: Project, state: _CompilerState) -> SignalMap:
    signal_map = SignalMap()

    for observation in project.control.observations:
        binding = _build_observation_binding(sensor_element, observation, state)
        if binding is not None:
            signal_map.observations.append(binding)

    for command in project.control.commands:
        binding = _build_command_binding(command, state)
        if binding is not None:
            signal_map.commands.append(binding)

    return signal_map


def _build_observation_binding(
    sensor_element: Element,
    observation: ObservationChannel,
    state: _CompilerState,
) -> SignalBinding | None:
    coordinate_id = _extract_leaf_ref(observation.source_ref, "coordinates")
    if coordinate_id is None:
        state.report.add_warning(
            code="signal.observation_unresolved",
            message=(
                f"Observation {observation.id!r} uses unsupported source_ref "
                f"{observation.source_ref!r}."
            ),
            location=f"control.observations[{observation.id}]",
        )
        return None

    joint_name = state.coordinate_joint_names.get(coordinate_id)
    if joint_name is None:
        state.report.add_warning(
            code="signal.observation_joint_missing",
            message=(
                f"Observation {observation.id!r} references coordinate {coordinate_id!r}, "
                "which was not lowered into a MuJoCo joint."
            ),
            location=f"control.observations[{observation.id}]",
        )
        return None

    backend_name = f"observation_{observation.id}"
    SubElement(sensor_element, "jointpos", {"name": backend_name, "joint": joint_name})
    return SignalBinding(
        signal_id=observation.id,
        external_name=observation.name,
        reference=observation.source_ref,
        backend_type="sensor/jointpos",
        backend_name=backend_name,
    )


def _build_command_binding(command: CommandChannel, state: _CompilerState) -> SignalBinding | None:
    system_id = _extract_leaf_ref(command.target_ref, "systems")
    actuator_id = _extract_leaf_ref(command.target_ref, "actuators")
    if actuator_id is None:
        state.report.add_warning(
            code="signal.command_unresolved",
            message=(
                f"Command {command.id!r} uses unsupported target_ref {command.target_ref!r}."
            ),
            location=f"control.commands[{command.id}]",
        )
        return None

    backend_name = state.actuator_names.get((system_id, actuator_id)) or state.actuator_names.get((None, actuator_id))
    if backend_name is None:
        state.report.add_warning(
            code="signal.command_target_missing",
            message=(
                f"Command {command.id!r} references actuator {actuator_id!r}, which was "
                "not lowered into MJCF."
            ),
            location=f"control.commands[{command.id}]",
        )
        return None

    return SignalBinding(
        signal_id=command.id,
        external_name=command.name,
        reference=command.target_ref,
        backend_type="actuator",
        backend_name=backend_name,
    )


def _extract_leaf_ref(reference: str, collection_name: str) -> str | None:
    parts = [part for part in reference.split("/") if part]
    for index, part in enumerate(parts[:-1]):
        if part == collection_name:
            return parts[index + 1]
    return None


def _geometry_size_string(geometry: Geometry) -> str | None:
    value = geometry.parameters.get("size")
    if isinstance(value, (tuple, list)):
        return _format_scalars(*[float(component) for component in value])
    if isinstance(value, (int, float)):
        return _format_scalars(float(value))
    if geometry.kind == "sphere":
        radius = geometry.parameters.get("radius")
        if isinstance(radius, (int, float)):
            return _format_scalars(float(radius))
    if geometry.kind == "cylinder":
        radius = geometry.parameters.get("radius")
        half_height = geometry.parameters.get("half_height")
        if isinstance(radius, (int, float)) and isinstance(half_height, (int, float)):
            return _format_scalars(float(radius), float(half_height))
    return None


def _mujoco_actuator_element_name(kind: ActuatorKind) -> str:
    if kind == ActuatorKind.POSITION:
        return "position"
    return "motor"


def _body_name(system_id: str, link_id: str) -> str:
    return f"{system_id}_link_{link_id}"


def _format_scalar(value: float) -> str:
    return f"{value:.6g}"


def _format_scalars(*values: float) -> str:
    return " ".join(_format_scalar(value) for value in values)


def _format_vec3(value: Vec3) -> str:
    return _format_scalars(*value)


def _format_quat(value: tuple[float, float, float, float]) -> str:
    return _format_scalars(*value)


def _format_inertia6(value: tuple[float, float, float, float, float, float]) -> str:
    return _format_scalars(*value)

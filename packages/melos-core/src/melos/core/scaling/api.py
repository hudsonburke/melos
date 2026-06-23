from __future__ import annotations
import copy

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from melos.core.common.types import Transform, Vec3
from melos.core.project.model import Project
from melos.core.retarget.model import SegmentMeasurementSet
from melos.core.scaling.factors import JointCorrespondenceMap, ScaleFactorMap, compute_scale_factors
from melos.core.scaling.inertials import scale_inertial
from melos.core.scaling.skeleton import extract_skeleton_tree
from melos.core.system.model import Geometry, Link, Site, SystemModel

MeasurementInput = SegmentMeasurementSet | Mapping[str, float]
SegmentScaleLinkMap = Mapping[str, Sequence[str] | str]

_LENGTH_UNITS_TO_METERS: dict[str, float] = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
}


@dataclass(slots=True, kw_only=True)
class SystemScaleFitResult:
    """Result of fitting one project's articulated system to target measurements."""

    project: Project
    system_id: str
    source_measurements: dict[str, float] = field(default_factory=dict)
    target_measurements: dict[str, float] = field(default_factory=dict)
    segment_scale_factors: dict[str, float] = field(default_factory=dict)
    link_scale_factors: ScaleFactorMap = field(default_factory=dict)
    source_units: str = "m"
    target_units: str = "m"


def _scale_transform_translation(transform: Transform, scale_factor: float) -> Transform:
    translation = transform.translation
    return Transform(
        translation=(
            translation[0] * scale_factor,
            translation[1] * scale_factor,
            translation[2] * scale_factor,
        ),
        rotation=transform.rotation,
    )


def _scale_link_geometry_parameters(parameters: dict[str, object], scale_factor: float) -> dict[str, object]:
    scaled: dict[str, object] = {}
    for key, value in parameters.items():
        if isinstance(value, (int, float)) and key in {
            "radius",
            "height",
            "length",
            "size_x",
            "size_y",
            "size_z",
        }:
            scaled[key] = float(value) * scale_factor
        elif (
            isinstance(value, (tuple, list))
            and len(value) == 3
            and all(isinstance(component, (int, float)) for component in value)
            and key in {"size", "half_extents"}
        ):
            scaled[key] = [float(component) * scale_factor for component in value]
        else:
            scaled[key] = value
    return scaled


def _resolve_target_system(project: Project, system_id: str | None = None) -> SystemModel:
    if system_id is not None:
        system = project.get_system(system_id) if hasattr(project, "get_system") else None
        if system is None:
            raise ValueError(f"Project does not contain system {system_id!r}.")
        return system

    anatomical_system = project.get_anatomical_system() if hasattr(project, "get_anatomical_system") else None
    if anatomical_system is not None:
        return anatomical_system
    if project.systems:
        return project.systems[0]
    raise ValueError("Project does not contain any systems to scale.")


def _measurement_dict_and_units(
    measurements: MeasurementInput,
    units: str | None,
) -> tuple[dict[str, float], str]:
    if hasattr(measurements, "as_dict") and callable(measurements.as_dict):
        return measurements.as_dict(), units or getattr(measurements, "units", "m")
    return dict(measurements), units or "m"


def _length_unit_to_meters(units: str | None) -> float:
    normalized = (units or "m").strip().lower()
    factor = _LENGTH_UNITS_TO_METERS.get(normalized)
    if factor is None:
        raise ValueError(
            f"Unsupported length units {units!r}. Expected one of: {sorted(_LENGTH_UNITS_TO_METERS)}"
        )
    return factor


def _normalize_segment_scale_link_ids(segment_to_link_ids: SegmentScaleLinkMap) -> dict[str, tuple[str, ...]]:
    normalized: dict[str, tuple[str, ...]] = {}
    for segment_id, raw_link_ids in segment_to_link_ids.items():
        if isinstance(raw_link_ids, str):
            link_ids = (raw_link_ids,)
        else:
            link_ids = tuple(str(link_id) for link_id in raw_link_ids)
        if not link_ids:
            continue
        normalized[str(segment_id)] = link_ids
    return normalized


def compute_segment_scale_factors_from_measurements(
    source_measurements: MeasurementInput,
    target_measurements: MeasurementInput,
    *,
    source_units: str | None = None,
    target_units: str | None = None,
) -> dict[str, float]:
    """Return per-segment scale factors that resize source measurements to target measurements.

    Segment factors are computed as:

        target_length_in_source_units / source_length

    Only segment IDs present in both inputs and with positive lengths are returned.
    """

    source_by_segment, effective_source_units = _measurement_dict_and_units(
        source_measurements,
        source_units,
    )
    target_by_segment, effective_target_units = _measurement_dict_and_units(
        target_measurements,
        target_units,
    )

    target_to_source_units = (
        _length_unit_to_meters(effective_target_units)
        / _length_unit_to_meters(effective_source_units)
    )

    scale_factors: dict[str, float] = {}
    for segment_id in sorted(set(source_by_segment) & set(target_by_segment)):
        source_length = float(source_by_segment[segment_id])
        target_length = float(target_by_segment[segment_id]) * target_to_source_units
        if source_length <= 1e-8 or target_length <= 1e-8:
            continue
        scale_factors[segment_id] = target_length / source_length
    return scale_factors


def link_scale_factors_from_segment_scale_factors(
    segment_scale_factors: Mapping[str, float],
    segment_to_link_ids: SegmentScaleLinkMap,
) -> ScaleFactorMap:
    """Project per-segment scale factors onto the link IDs that encode those segment lengths."""

    normalized_map = _normalize_segment_scale_link_ids(segment_to_link_ids)
    link_scale_factors: ScaleFactorMap = {}
    for segment_id, link_ids in normalized_map.items():
        scale_factor = segment_scale_factors.get(segment_id)
        if scale_factor is None or scale_factor <= 1e-8:
            continue
        for link_id in link_ids:
            link_scale_factors[link_id] = scale_factor
    return link_scale_factors


def scale_system(
    system: SystemModel,
    link_scale_factors: Mapping[str, float],
) -> SystemModel:
    """Return a scaled copy of *system* using per-link translation scale factors."""

    scale_factors = {str(link_id): float(scale) for link_id, scale in link_scale_factors.items()}

    scaled_links = [
        Link(
            id=link.id,
            name=link.name,
            transform=_scale_transform_translation(link.transform, scale_factors.get(link.id, 1.0)),
            inertial=scale_inertial(link.inertial, scale_factors.get(link.id, 1.0)),
            asset_ids=list(link.asset_ids),
            description=link.description,
            annotations=dict(link.annotations),
        )
        for link in system.links
    ]
    scaled_sites = [
        Site(
            id=site.id,
            name=site.name,
            link_id=site.link_id,
            parent_site_id=site.parent_site_id,
            transform=_scale_transform_translation(
                site.transform,
                scale_factors.get(site.link_id, 1.0) if site.link_id is not None else 1.0,
            ),
            tags=list(site.tags),
            description=site.description,
            annotations=dict(site.annotations),
        )
        for site in system.sites
    ]
    scaled_geometries = [
        Geometry(
            id=geometry.id,
            name=geometry.name,
            kind=geometry.kind,
            role=geometry.role,
            link_id=geometry.link_id,
            site_id=geometry.site_id,
            transform=_scale_transform_translation(
                geometry.transform,
                scale_factors.get(geometry.link_id, 1.0) if geometry.link_id is not None else 1.0,
            ),
            parameters=_scale_link_geometry_parameters(
                dict(geometry.parameters),
                scale_factors.get(geometry.link_id, 1.0) if geometry.link_id is not None else 1.0,
            ),
            asset_id=geometry.asset_id,
            description=geometry.description,
            annotations=dict(geometry.annotations),
        )
        for geometry in system.geometries
    ]
    return SystemModel(
        id=system.id,
        name=system.name,
        role=system.role,
        root_link_id=system.root_link_id,
        description=system.description,
        asset_ids=list(system.asset_ids),
        links=scaled_links,
        joints=list(system.joints),
        sites=scaled_sites,
        geometries=scaled_geometries,
        actuators=list(system.actuators),
        sensors=list(system.sensors),
        annotations=dict(system.annotations),
    )


def scale_project_system(
    project: Project,
    link_scale_factors: Mapping[str, float],
    *,
    system_id: str | None = None,
) -> Project:
    """Return a cloned project whose selected system is scaled by *link_scale_factors*."""

    cloned = copy.deepcopy(project)
    target_system = _resolve_target_system(cloned, system_id)
    scaled_system = scale_system(target_system, link_scale_factors)
    cloned.systems = [
        scaled_system if system.id == target_system.id else system
        for system in cloned.systems
    ]
    return cloned


def fit_project_system_to_measurements(
    project: Project,
    source_measurements: MeasurementInput,
    target_measurements: MeasurementInput,
    segment_to_link_ids: SegmentScaleLinkMap,
    *,
    system_id: str | None = None,
    source_units: str | None = None,
    target_units: str | None = None,
) -> SystemScaleFitResult:
    """Scale one project system so its measured segments match target measurements.

    The caller provides source/target segment measurements and a map from segment IDs
    to the link IDs whose local translations encode those segment lengths.
    """

    source_by_segment, effective_source_units = _measurement_dict_and_units(
        source_measurements,
        source_units,
    )
    target_by_segment, effective_target_units = _measurement_dict_and_units(
        target_measurements,
        target_units,
    )
    segment_scale_factors = compute_segment_scale_factors_from_measurements(
        source_by_segment,
        target_by_segment,
        source_units=effective_source_units,
        target_units=effective_target_units,
    )
    link_scale_factors = link_scale_factors_from_segment_scale_factors(
        segment_scale_factors,
        segment_to_link_ids,
    )
    scaled_project = scale_project_system(
        project,
        link_scale_factors,
        system_id=system_id,
    )
    scaled_system = _resolve_target_system(scaled_project, system_id)
    return SystemScaleFitResult(
        project=scaled_project,
        system_id=scaled_system.id,
        source_measurements=source_by_segment,
        target_measurements=target_by_segment,
        segment_scale_factors=segment_scale_factors,
        link_scale_factors=link_scale_factors,
        source_units=effective_source_units,
        target_units=effective_target_units,
    )


def scale_model(
    project: Project,
    link_vectors: dict[str, Vec3],
    joint_map: JointCorrespondenceMap,
) -> Project:
    cloned = copy.deepcopy(project)

    if not joint_map or not link_vectors:
        return cloned

    anatomical_system = cloned.get_anatomical_system()
    if anatomical_system is None:
        raise ValueError("Project does not contain an anatomical system to scale.")

    link_ids = {link.id for link in anatomical_system.links}
    for joint_name, link_id in joint_map.items():
        if link_id not in link_ids:
            raise ValueError(
                f"joint_map references link '{link_id}' (for joint '{joint_name}') "
                f"which does not exist in the project."
            )

    skeleton = extract_skeleton_tree(anatomical_system)
    scale_factors: ScaleFactorMap = compute_scale_factors(skeleton, link_vectors, joint_map)
    scaled_anatomical_system = scale_system(anatomical_system, scale_factors)
    cloned.systems = [
        scaled_anatomical_system if system.id == anatomical_system.id else system
        for system in cloned.systems
    ]
    return cloned

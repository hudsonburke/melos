# melos.core API Reference

This reference covers the canonical core API used by the current melos architecture.

## Core project model

Primary modules:

- `melos.core.project.model`
- `melos.core.project.skin`
- `melos.core.system.model`
- `melos.core.system.enums`
- `melos.core.retarget.model`
- `melos.core.retarget.translation`
- `melos.core.retarget.measurements`
- `melos.core.kinematics.pose`
- `melos.core.validation`

## `Project`

```python
@dataclass(slots=True, kw_only=True)
class Project:
    schema_version: str
    meta: ProjectMeta
    assets: AssetLibrary
    systems: list[SystemModel]
    assemblies: list[SystemAssembly]
    simulation: SimulationConfig
    control: ControlInterface
    translation_maps: list[TranslationMap]
    skin_attachments: list[SkinAttachment]
```

Convenience helpers:

- `get_system(system_id)`
- `get_systems_by_role(role)`
- `get_primary_system_by_role(role)`
- `get_anatomical_system()`

## `SystemModel`

```python
@dataclass(slots=True, kw_only=True)
class SystemModel:
    id: SystemId
    name: str
    role: SystemRole = SystemRole.CUSTOM
    root_link_id: LinkId | None = None
    description: str = ""
    asset_ids: list[AssetId] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    joints: list[Joint] = field(default_factory=list)
    sites: list[Site] = field(default_factory=list)
    geometries: list[Geometry] = field(default_factory=list)
    actuators: list[Actuator] = field(default_factory=list)
    sensors: list[Sensor] = field(default_factory=list)
    profile: dict[str, object] = field(default_factory=dict)
    annotations: dict[str, object] = field(default_factory=dict)
```

Supporting dataclasses:

- `Link`
- `Joint`
- `Site`
- `Geometry`
- `Actuator`
- `Sensor`
- `AssemblyEndpoint`
- `AssemblyConnection`
- `CoordinateCoupling`
- `SystemAssembly`

Key enums:

- `SystemRole`
- `GeometryRole`
- `ActuatorKind`
- `SensorKind`
- `InterfaceKind`
- `ConnectionKind`
- `ConstraintPolicy`

## Skin attachments

```python
@dataclass(slots=True, kw_only=True)
class SkinAttachment:
    id: str
    name: str
    target_system_id: str
    mesh_asset_id: str | None = None
    binding_asset_id: str | None = None
    fit: SkinAttachmentFit | None = None
    translation_map_id: str | None = None
    binding_mode: str = "link_linear_blend"
```

Fit metadata uses:

- `anchor_link_id`
- `reference_link_ids`
- `reference_site_ids`
- `reference_geometry_ids`

## Retarget and translation data

```python
@dataclass(slots=True, kw_only=True)
class JointPositionSet:
    positions: dict[str, Vec3]
    space: str = "world"
    units: str = "m"
```

```python
@dataclass(slots=True, kw_only=True)
class SegmentMeasurement:
    segment_id: str
    length: float
    source_joint_names: list[str]
```

```python
@dataclass(slots=True, kw_only=True)
class SegmentTranslationRule:
    segment_id: str
    source_link_id: str
    target_link_id: str
    parent_segment_id: str | None = None
    target_joint_ids: list[str] = field(default_factory=list)
    anchor_target_joint_id: str | None = None
    reduction_mode: str = "direct"
    failure_policy: str = "required"
    template_ref_dir: tuple[float, float, float] = (0.0, 0.0, 1.0)
    aliases: list[str] = field(default_factory=list)
```

```python
@dataclass(slots=True, kw_only=True)
class TranslationMap:
    id: str
    source_rig: str
    target_rig: str
    version: str
    rules: list[SegmentTranslationRule] = field(default_factory=list)
```

Helper functions:

- `compute_segment_measurements_from_rules(...)`
- `evaluate_system_world_transforms(system, coordinate_values=None)`
- `scale_model(project, link_vectors, joint_map)`

## Scaling contract

`melos.core.scaling.scale_model(...)` scales the primary anatomical system in a project.

Inputs:

- `project`: canonical project with a anatomical `SystemModel`
- `link_vectors`: parent-relative segment vectors keyed by joint name
- `joint_map`: maps joint names to child link IDs in the anatomical system

The result is a new scaled `Project`.

## Validation

Use:

- `validate_project(project)`

Validation covers:

- references
- topology
- transforms

## JSON I/O

Use:

- `load_project(path)`
- `save_project(project, path)`
- `project_to_dict(project)`
- `project_from_dict(data)`

## Notes

The old anatomical/device/assembly split is no longer part of the supported public architecture. New code should target the canonical system-based API shown above.

# melos-core Developer Guide

This guide is for contributors changing the canonical `melos.core` model, validation, JSON I/O, or subject-scaling logic. For a compact API list, see `docs/core-api-reference.md`.

## Role of `melos.core`

`melos.core` is the backend language shared by Blender, skin/model adapters, and simulation compilers. It must stay pure Python and backend-neutral.

Hard boundaries:

- `melos.core` may not import `bpy`, MuJoCo, `numpy`, `torch`, or Blender package modules.
- Frontends/backends may import `melos.core`.
- Domain semantics belong in typed core dataclasses and enums, not in Blender custom-property names or MJCF XML conventions.
- Validation is explicit: constructors should be cheap and permissive; `melos.core.validation.validate_project()` reports bad references, topology, and transforms.

## Current package map

```text
melos.core
├── project/      Project aggregate, metadata, skin attachments
├── system/       SystemModel, links, joints, sites, geometries, actuators, assemblies
├── kinematics/   Coordinate definitions, joint/coordinate enums, pose evaluation
├── assets/       AssetLibrary and asset descriptors
├── simulation/   Backend-neutral simulation configuration
├── control/      Command and observation interface definitions
├── retarget/     Translation maps, segment rules, measurement helpers
├── scaling/      Pure functions that return scaled Project instances
├── validation/   Reference, topology, and transform validation passes
├── io/           JSON structure/unstructure and schema migrations
├── common/       IDs, types, transforms, units, metadata, inertial mechanics
├── actuator/     Muscle-specific auxiliary models
└── contact/      Contact/collision descriptors; not yet integrated into Project
```

Prefer extending these modules over creating parallel subject/device schemas. The supported public architecture is `Project -> systems + assemblies + skin_attachments`.

## Canonical aggregate

`Project` (`melos.core.project.model`) is the only root object handed between packages.

Important fields:

- `meta`: stable project identity and provenance.
- `assets`: reusable mesh/texture/geometry assets.
- `systems`: `SystemModel` instances. Use `SystemRole.ANATOMICAL` for the subject, `SystemRole.DEVICE` for exoskeletons/devices, and other roles only when needed.
- `assemblies`: `SystemAssembly` objects that describe connections/couplings between systems.
- `simulation`: backend-neutral timestep/gravity/solver config.
- `control`: backend-neutral command and observation declarations.
- `translation_maps`: retargeting and semantic correspondence rules.
- `skin_attachments`: deformable skin/binding metadata attached to a target system.

Helpers such as `get_system()`, `get_systems_by_role()`, and `get_anatomical_system()` are convenience lookups only. They do not validate uniqueness beyond returning the first matching object.

## `SystemModel` invariants

`SystemModel` is the common representation for subjects and devices.

```python
SystemModel(
    id="subject",
    name="Subject",
    role=SystemRole.ANATOMICAL,
    root_link_id="pelvis",
    links=[...],
    joints=[...],
    sites=[...],
    geometries=[...],
    actuators=[...],
    sensors=[...],
)
```

Use the same primitives everywhere:

- `Link`: rigid body/device segment. `transform` is parent-relative where hierarchy exists. `inertial` is optional but should be SI.
- `Site`: named frame/point attached to a link or another site. Use sites for authoring handles, interfaces, tendon anchors, wrap side-sites, and sensor frames.
- `Joint`: relationship between `parent_link_id` and `child_link_id`; coordinates live on the joint as `CoordinateDefinition` values.
- `Geometry`: visual/collision/wrap/contact/fitting primitive attached to a link or site. `parameters` holds primitive-specific values until a typed model is justified.
- `Actuator`: generic driving primitive; `joint_id`/`coordinate_id` drive coordinates, `route` drives routed tendon/cable/muscle paths.
- `Sensor`: generic observation primitive attached to a link or site.

Model references are by stable IDs, never object identity. Validation owns dangling-reference detection.

## IDs, names, and annotations

- IDs are stable references. Do not regenerate them from display names during import/export.
- Names are display labels and may change without breaking references.
- Use existing ID aliases (`SystemId`, `LinkId`, `SiteId`, etc.) for type clarity.
- Put structured extension data in typed fields when it is part of the supported schema.
- Use `annotations` only for non-critical metadata that downstream packages can ignore safely.

## Units and transforms

Core uses SI units: meters, kilograms, seconds, radians, newtons, newton-meters.

Transform rules:

- Use `Transform` from `melos.core.common.types`.
- Link transforms and site transforms should be local/parent-relative unless a function explicitly states world space.
- Do not store Blender matrices, MuJoCo quaternions, or OpenSim axis conventions in core models. Convert at the adapter boundary.

## Routed actuators and cable paths

Routed force elements use `Actuator.route`.

```python
Actuator(
    id="exo_cable",
    name="Exo Cable",
    kind=ActuatorKind.CABLE,
    route=[
        RouteNode(kind=RouteNodeKind.SITE, site_id="anchor"),
        RouteNode(kind=RouteNodeKind.WRAP, geometry_id="pulley", side_site_id="pulley_side"),
        RouteNode(kind=RouteNodeKind.SITE, site_id="insertion"),
    ],
    cable=CableParameters(stiffness=1200.0, damping=2.0),
)
```

Route-node contract:

- `RouteNodeKind.SITE` requires `site_id`.
- `RouteNodeKind.WRAP` requires `geometry_id`; `side_site_id` is optional but recommended when the compiler/backend needs disambiguation.
- Wrap geometries should be `Geometry(role=GeometryRole.WRAP, ...)`.
- A meaningful cable route needs at least two ordered nodes; validation warns on underspecified topology.

Compiler-specific lowering remains outside core. Core only states ordered routing intent and typed cable parameters.

## Assemblies and couplings

Use assemblies for relationships between systems, not for intra-system joints.

- `AssemblyEndpoint` references one system's native primitives.
- `AssemblyConnection` describes an interface connection and optional `ConstraintPolicy`.
- `CoordinateCoupling` describes scalar coordinate relationships across or within systems.

The core model can represent these semantics even when a backend does not lower every policy yet. Validation should still catch dangling referenced systems, links, sites, geometries, and coordinates.

## Validation development

Standard validation entrypoint:

```python
from melos.core.validation import validate_project

report = validate_project(project)
if report.has_errors:
    ...
```

Passes run in this order:

1. `validation.references`: dangling IDs, missing referenced systems/primitives.
2. `validation.topology`: graph and structural rules.
3. `validation.transforms`: numeric transform sanity.

When adding validation:

- Emit `ValidationIssue` with stable `code`, human-readable `message`, precise `location`, and `ValidationSeverity`.
- Use warnings for degraded/underspecified but serializable intent.
- Use errors for missing required references or structures a compiler cannot safely interpret.
- Do not throw on the first issue unless the input shape prevents continuing.
- Add tests for both the valid case and the invalid/warning case.

Location strings should be specific enough to map back to authoring UI, e.g. `systems[exo].actuators[exo_cable].route[1].geometry_id`.

## JSON I/O and schema changes

Public helpers live in `melos.core.io.json`:

- `project_to_dict(project)`
- `project_to_json(project)`
- `save_project(project, path)`
- `project_from_dict(data)`
- `project_from_json(payload)`
- `load_project(path)`

The structurer rebuilds dataclasses and `StrEnum` values from JSON-compatible dictionaries. New dataclass fields should be backward compatible by having defaults or `default_factory` values.

When changing the schema:

1. Add the typed field or enum.
2. Give additive fields safe defaults.
3. Update migrations only if old JSON needs transformation beyond dataclass defaults.
4. Add JSON round-trip coverage.
5. Update Blender import/export and simulation compiler behavior if the field crosses package boundaries.

## Scaling development

`melos.core.scaling.scale_model()` returns a new `Project`; do not mutate the input project.

Scaling code should preserve:

- stable IDs and references,
- system topology,
- canonical SI units,
- asset references unless a real generated asset replaces them,
- validation behavior before and after scaling.

Add focused tests for the primitive being scaled and at least one integration-style test if references cross links/sites/geometries/muscles.

## Adding a new core feature

Use this checklist for any feature that becomes part of the canonical schema:

1. Add or extend dataclasses/enums in the owning core module.
2. Keep constructors defaultable and cheap.
3. Add reference validation for every new ID field.
4. Add topology validation for structural invariants.
5. Add JSON round-trip tests.
6. Update Blender builder/importer if the feature is authorable.
7. Update MuJoCo/backend compiler if the feature has runtime meaning.
8. Update docs when the public contract changes.

Avoid introducing parallel abstractions that encode the same concept in several packages. If Blender and MuJoCo both need the concept, it belongs in `melos.core` first.

## Testing patterns

Core tests live primarily in `packages/melos-core/tests/`.

Useful test categories:

- model construction and JSON round-trip (`test_json_roundtrip.py`, system-model tests),
- validation behavior (`test_validation.py`, focused feature tests),
- Blender fake-bpy builders/importers when the core feature is authorable,
- compiler tests when the core feature must lower to MJCF.

Run the focused tests you changed first, then the full relevant package set before merging:

```bash
python3 -m pytest packages/melos-core/tests -q
python3 -m pytest packages/melos-core/tests packages/melos-sim packages/melos-skin/tests packages/melos-blender/tests -q
```

Some optional tests skip when heavy extras are not installed; do not replace real validation with mocks.

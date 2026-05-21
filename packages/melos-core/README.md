# melos Core

`melos-core` is the foundational distribution for the melos ecosystem.

It provides the `melos.core` Python package: a thin, portable model-definition and validation layer for subject-specific musculoskeletal models, assistive devices, assembly metadata, and downstream simulation/control workflows.

The goal is not to replace Blender or MuJoCo.

- `melos.core` owns the canonical semantics and schema.
- The canonical architecture is now centered on `SystemModel`, `SystemAssembly`, retarget/measurement helpers, and system-aware skin attachments.
- `melos.core` also owns subject-specific scaling via `melos.core.scaling.scale_model()`.
- `melos.blender` provides authoring and editing workflows.
- `melos.sim.mujoco` provides MJCF compilation/export and runtime-facing helpers.

## Namespace Strategy

This repository intentionally uses a `src` layout with a PEP 420 namespace package.

- Distribution name: `melos-core`
- Import path: `melos.core`
- Future sibling distributions can provide:
  - `melos.blender`
  - `melos.sim.mujoco`
  - `melos.control`

Important: there is no `src/melos/__init__.py`. That is deliberate so multiple distributions can share the `melos` namespace cleanly.

## Repository Strategy

This repository is already organized as a monorepo with multiple installable packages under the shared `melos` namespace.

- keep package boundaries strict
- keep installation choices separate
- keep development close while the compiler contract evolves

## Why This Layer Exists

Neither Blender nor MJCF alone is a good canonical source of truth for the full workflow.

- Blender is excellent for visual authoring, MRI-aligned geometry, landmarks, and device layout, but it is not a portable simulation schema.
- MuJoCo is excellent for runtime simulation, contacts, sensors, actuators, and control, but it is too low-level to fully represent authoring intent, anatomy provenance, and device-attachment semantics.
- `melos.core` exists to hold the small amount of domain structure needed between those worlds.

The intended pattern is:

1. author or edit a project in Blender
2. convert scene state into `melos.core` models
3. validate and enrich the project in `melos.core`
4. optionally scale the project to subject-specific proportions in `melos.core`
5. compile/export to MuJoCo and other downstream targets

## Scope

### v0.1 (Current)

The v0.1 implementation includes:

- canonical articulated-system models with links, joints, sites, geometries, sensors, actuators, and interfaces
- system assemblies and coordinate couplings
- system-aware skin attachments with link-based bindings
- system-centric project/schema definitions used across frontends and backends
- comprehensive asset references with defined roles (imaging, segmentation, visual, collision, simulation)
- expanded simulation configuration with solver settings, integrator, timestep, gravity, and keyframes
- control interface definitions for observations and commands
- contact geometry models and collision pair definitions
- muscles with path points, physiology parameters, and path-based line-of-action
- wrap geometry support for muscles (cylindrical, sphere, ellipsoid wrappers)
- full validation of references, topology, and transforms
- JSON round-trip serialization with schema versioning
- subject-specific scaling of canonical subject-system structure and related subject-space data

### v0.2+

Future extensions:

- structure-first template import from OpenSim and Rajagopal models
- richer inertial-property provenance and metadata
- subject-specific fitting metadata for device attachment
- more detailed controller and estimator contracts
- additional simulation backends beyond MuJoCo

## Design Principles

- thin layer, not a second simulator
- explicit SI units everywhere
- frame-first modeling
- stable IDs separate from display names
- backend-neutral semantics, with a practical bias toward MuJoCo export
- explicit asset roles such as imaging, segmentation, visual, collision, and simulation
- versioned, serializable project model
- typed models first; UI and engine adapters second

## Package Layout

```text
src/
  melos/
    core/
      __init__.py
      py.typed
      common/
        __init__.py
        ids.py
        types.py
        mechanics.py
        enums.py
        units.py
        transforms.py
        metadata.py
      kinematics/
        __init__.py
        enums.py
        model.py
      project/
        __init__.py
        model.py
      assets/
        __init__.py
        model.py
      subject/
        __init__.py
        model.py
        muscles/
          __init__.py
          ids.py
          enums.py
          model.py
          wraps.py
          geometry.py
      device/
        __init__.py
        enums.py
        model.py
      assembly/
        __init__.py
        model.py
      contact/
        __init__.py
        enums.py
        model.py
      simulation/
        __init__.py
        enums.py
        contract.py
        model.py
      control/
        __init__.py
        model.py
      io/
        __init__.py
        json.py
        schema.py
        migrations.py
      validation/
        __init__.py
        references.py
        topology.py
        transforms.py
      scaling/
        __init__.py
        api.py
        factors.py
        geometry.py
        inertials.py
        muscles.py
        skeleton.py
tests/
  test_smoke.py
  # ... additional tests in the full suite
```

## What Each Module Should Contain

### `src/melos/core/__init__.py`

- package-level metadata for `melos.core`
- no heavy imports or domain logic
- light re-exports only after the public API stabilizes

### `src/melos/core/common/ids.py`

- canonical ID types and naming rules
- helpers for stable subject, device, frame, and asset identifiers
- reference-friendly types used across all domains

### `src/melos/core/common/types.py`

- small reusable type aliases and base dataclasses
- examples: `Vec3`, `Quat`, `Inertia6`, `Transform`
- only low-level value objects, not subject/device/domain aggregates

### `src/melos/core/common/mechanics.py`

- mechanics-oriented shared dataclasses
- examples: inertial properties and related physical-property records used across subject and device domains

### `src/melos/core/common/enums.py`

- shared enums used across the whole project model
- examples: asset roles and compile targets

### `src/melos/core/kinematics/enums.py`

- shared enums for joint and coordinate semantics used by both subject and device domains

### `src/melos/core/kinematics/model.py`

- shared kinematic dataclasses
- examples: coordinate definitions used by subject joints and device joints

### `src/melos/core/common/units.py`

- unit conventions and helpers
- this should document the rule that the core model uses SI units internally
- importers/exporters can convert here rather than scattering conversions elsewhere

### `src/melos/core/common/transforms.py`

- transform math conventions and helpers
- parent-relative frame handling
- canonical rotation conventions for the project
- shared transform math used by importers, scaling, and compilers without introducing backend dependencies

### `src/melos/core/scaling/`

- pure-Python subject-specific model scaling
- `scale_model(project, subject_joints, joint_map) -> Project`
- derives per-body scale factors from parent-relative joint vectors and body transforms
- scales subject geometry, muscles, wraps, contacts, and inertials while preserving IDs and topology

### `src/melos/core/common/metadata.py`

- schema metadata, provenance metadata, and annotation containers
- project-level provenance should stay structured instead of becoming arbitrary dicts everywhere

### `src/melos/core/project/model.py`

- the top-level aggregate model, `Project`
- should own schema version, project metadata, subject, devices, assembly, simulation, and control
- this is the canonical handoff object between adapters/backends

### `src/melos/core/assets/model.py`

- asset registry and asset reference models
- distinguish imaging, segmentation, visual, collision, and simulation assets
- track provenance, source paths, and intended usage roles

### `src/melos/core/subject/model.py`

- anatomy-facing model definitions
- bodies, joints, frames, landmarks, inertial properties
- subject-level container that also references muscle and wrap entities

### `src/melos/core/subject/muscles/model.py`

- canonical muscle definitions
- physiology, ordered path points, and path-level metadata
- path-based line-of-action remains canonical even when geometry is present

### `src/melos/core/subject/muscles/ids.py`

- ID aliases owned by the muscle subdomain
- keeps muscle-only identifiers out of the shared global ID module

### `src/melos/core/subject/muscles/enums.py`

- enums owned by the muscle subdomain
- examples: path point kinds, wrap geometry kinds, line-of-action source, and preferred representation

### `src/melos/core/subject/muscles/wraps.py`

- wrap geometry definitions associated with the subject
- should support shared wrap objects that influence multiple muscles
- common wrap kinds should use typed parameter dataclasses instead of loose dictionaries

### `src/melos/core/subject/muscles/geometry.py`

- optional muscle-associated geometry metadata
- visualization meshes, centerline sources, and future volumetric hints

### `src/melos/core/device/model.py`

- assistive-device model definitions
- links, joints, frames, sensors, actuators, interfaces, and device assets
- should not assume exoskeleton-only semantics, but can bias toward them

### `src/melos/core/device/enums.py`

- enums owned by the device subdomain
- examples: sensor kinds, actuator kinds, and physical interface kinds

### `src/melos/core/assembly/model.py`

- how subject and device come together
- attachments, calibration transforms, couplings, interface definitions, and contact-relevant links
- this is where subject-specific exoskeleton fitting semantics should live

### `src/melos/core/contact/model.py`

- collision geometry definitions for subject bodies and device links
- contact pair definitions specifying which bodies should interact
- geometry kinds, dimensions, and parameters (e.g., sphere radius, cylinder height)

### `src/melos/core/contact/enums.py`

- enums for contact configuration
- examples: geometry kinds (sphere, cylinder, capsule, ellipsoid, mesh, plane)

### `src/melos/core/simulation/model.py`

- backend-neutral simulation settings
- gravity, timestep, default state, asset-role selection, and compile preferences
- should stay thin and avoid reproducing a whole engine spec

### `src/melos/core/simulation/enums.py`

- enums for simulation configuration
- examples: solver types, integrator types

### `src/melos/core/simulation/contract.py`

- compiler-facing expectations for backend packages
- documents what a backend such as `melos.sim.mujoco` may assume about validated `melos.core` projects
- helps keep `melos.core` semantically rich without turning it into a backend-specific schema

### `src/melos/core/control/model.py`

- stable control and analysis interface definitions
- observation channels, command channels, units, signal names, and routing metadata
- these contracts should survive backend changes

### `src/melos/core/io/json.py`

- JSON serialization and deserialization for `Project`
- one clear place to define the portable on-disk format

### `src/melos/core/io/schema.py`

- schema version identifiers and schema-related helpers
- if formal JSON schema generation is added later, this is the natural home

### `src/melos/core/io/migrations.py`

- forward migrations between schema versions
- old project files should be upgraded here instead of handled ad hoc in importers

### `src/melos/core/validation/references.py`

- checks that all IDs and references resolve correctly
- examples: body refs, frame refs, asset refs, attachment refs

### `src/melos/core/validation/topology.py`

- structural validation
- examples: tree consistency, parent-child cycles, invalid couplings, disconnected attachments

### `src/melos/core/validation/transforms.py`

- transform-specific validation
- examples: finite values, normalized quaternions, frame consistency, invalid relative transforms

### `tests/test_smoke.py`

- minimal import-level smoke test for the namespace package
- should stay tiny and confirm that `melos.core` installs and imports correctly

## Roadmap

### Completed (v0.1)

1. Define cross-cutting conventions
   - SI units, frame conventions, quaternion ordering, ID rules
2. Implement `common` primitives
   - IDs, low-level types, transforms, metadata
3. Implement the top-level project model
   - `Project` and schema metadata
4. Implement domain models
   - subject, device, assembly, simulation, control, assets, contacts
5. Implement validation
   - references, topology, transforms
6. Implement portable I/O
   - JSON read/write and schema migrations
7. Add examples and smoke tests
8. Build adapters in sibling packages
   - `melos.blender` with authoring operators and panels
   - `melos.sim.mujoco` with MJCF compilation
9. Extend the subject model for muscles and wraps
   - muscle physiology, path points, wrap geometries (cylinder, sphere, ellipsoid)

### Future (v0.2+)

- Structure-first template import from OpenSim and Rajagopal models
- Richer inertial-property provenance and metadata storage
- Subject-specific fitting metadata for device attachment
- More detailed controller and estimator contracts
- Additional simulation backends beyond MuJoCo

## Development Notes

- keep domain models pure Python; no Blender or MuJoCo imports here
- prefer explicit dataclasses and enums over large untyped dictionaries
- avoid backend-specific assumptions in the canonical model unless they clearly simplify export
- keep the public API small until the schema stabilizes
- treat `Link.transform` as the canonical parent-relative link placement

## Example Fixtures

- example fixtures should use canonical `Project.systems`, `Project.assemblies`, and `SkinAttachment` data
- package tests provide the primary executable examples for the current schema

## MuJoCo Boundary

The `melos.core -> melos.sim.mujoco` boundary is intentionally compiler-like rather than one-to-one.

- `melos.core` owns authoring semantics: articulated systems, assemblies, assets, skin attachments, and stable control names
- `melos.core` owns subject-specific scaling as a canonical preprocessing step
- `melos.sim.mujoco` should own backend lowering into MJCF bodies, joints, sites, geoms, actuators, sensors, and backend-specific approximations

The current backend-facing expectations are documented in `src/melos/core/simulation/contract.py`.

## Quick Start

```bash
python3 -m pip install -e .[dev]
python3 -c "import melos.core; print(melos.core.__version__)"
pytest
```

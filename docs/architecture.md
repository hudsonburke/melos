# Melos Framework Architecture

Melos is a specialized simulation framework designed for physiological and robotic movement modeling. It provides a bridge between Blender as an authoring environment and MuJoCo as a high-performance physics engine, centered around a formal core domain model.

The canonical core architecture is based on `SystemModel`, `SystemAssembly`, and `SkinAttachment`.

## 1. System Overview

The framework is structured as four namespace packages that share the `melos` namespace via PEP 420. This architecture allows the core data models to remain decoupled from specific authoring, simulation, or pipelining implementations.

The canonical data flow follows a linear path:
**Skin/Pose Artifacts (Pipeline)** → **Core (Domain Models)** → **Blender (Authoring)** → **Optional Core Scaling** → **MuJoCo (Simulation)**

JSON serves as the portable interchange format, enabling projects to be serialized, versioned, and moved between tools without losing semantic information.

## 2. Package Dependency Graph

The dependency structure ensures that the domain logic remains pure and portable:

```
melos.blender → melos.core ← melos.sim.mujoco
                          ↑
                     melos.skin
```

- **melos.core**: Zero external dependencies. Contains all dataclass models, type definitions, and the validation engine.
- **melos.skin**: Depends on `melos.core` and `melos.sim`. Acts as the mediating layer between GEM/SOMA-X and the core model. It owns the heavy ML surface area (numpy, torch, trimesh), keeping `melos.core` pure Python.
- **melos.blender**: Depends on `bpy` (Blender Python API) and `melos.core`. It handles the mapping between Blender objects and core models.
- **melos.sim**: Simulation umbrella package. The current backend is `melos.sim.mujoco`, which depends on `melos.core`, uses the standard library `xml.etree` to generate MJCF (MuJoCo XML) files, and does not require the `mujoco` python package to perform compilation.
- **MJCF Import**: `melos.sim.mujoco.importers` uses Python's standard library `xml.etree.ElementTree` with built-in include resolution and default-class handling to parse MJCF files. No external dependencies are required.

## 3. The Project Aggregate

`Project` is the root aggregate containing the complete state of a simulation model. It uses Python 3.12 dataclasses with slots for memory efficiency and keyword-only arguments for clarity.

```python
@dataclass(slots=True, kw_only=True)
class Project:
    schema_version: str = "0.1.0"
    meta: ProjectMeta                 # id, name, description, created_by, created_at
    assets: AssetLibrary              # items: list[AssetRecord] — id, name, role, uri, media_type
    systems: list[SystemModel]        # canonical articulated systems
    assemblies: list[SystemAssembly]  # interface-centric connections/couplings
    simulation: SimulationConfig      # time_step, gravity, solver_type, integrator, solver_iterations, keyframes
    control: ControlInterface         # observations: list[ObservationChannel], commands: list[CommandChannel]
    translation_maps: list[TranslationMap]
    skin_attachments: list[SkinAttachment]
```

## 4. Type System Conventions

The framework enforces strict typing and unit consistency to prevent common modeling errors:

- **ID System**: All identifiers are `TypeAlias = str` defined in `common/ids.py` (e.g., `BodyId`, `FrameId`, `JointId`).
- **Geometric Primitives**:
  - `Vec3 = tuple[float, float, float]`
  - `Quat = tuple[float, float, float, float]`
  - `Transform(translation: Vec3, rotation: Quat)`: Immutable value type with an `identity()` classmethod.
  - `Inertia6 = tuple[float, float, float, float, float, float]`
- **Model Configuration**: All models use `@dataclass(slots=True, kw_only=True)`. `frozen=True` is reserved for small value types like `Transform`.
- **Enums**: All enumerations inherit from `StrEnum` with lowercase values to ensure JSON compatibility.
- **Units**: SI units are used throughout. Metadata on fields explicitly marks units (e.g., `field(metadata={"unit": LENGTH_UNIT})`).
- **Validation**: Models do not perform constructor validation. Integrity is maintained through a dedicated validation pass.

## 5. Canonical System Model

The `SystemModel` represents any articulated system in the project, including anatomicals, devices, and auxiliary articulated structures.

- **Link**: The fundamental rigid element. Contains `id`, `name`, a parent-relative `transform`, optional inertial properties, associated `asset_ids`, `description`, and `annotations`.
- **Joint**: Defines kinematics between links. Attributes include `id`, `kind`, `parent_link_id`, `child_link_id`, optional `parent_site_id` / `child_site_id`, and `coordinates`.
- **Site**: A named point or local frame attached to a link or another site. Sites cover landmark-like tags, anatomical anchors, and actuator path references.
- **Geometry**: Generic geometry attached to a link or site, with a semantic `role` and optional asset backing.
- **Actuator**: Generic actuation primitive, including muscle-like actuators expressed through `site_ids` and link references.
- **Sensor**: Generic observation primitive.
- **SystemRole**: Distinguishes anatomical, device, and custom systems.

### Scaling Pipeline (`melos.core.scaling`)

The scaling pipeline is a pure `melos.core` preprocessing step that adapts a generic anatomical system to anatomical-system-specific proportions without introducing backend coupling.

- `scale_model(project, link_vectors, joint_map) -> Project` returns a new project and does not mutate the input.
- `link_vectors` contains parent-relative segment vectors keyed by joint name.
- `joint_map` maps those joint names to child link IDs in the anatomical system.
- The implementation extracts a skeleton tree from anatomical-link translations, computes per-link isotropic scale factors, and propagates inherited scales breadth-first.
- The resulting scale factors are applied to link translations and related anatomical-space placements.

This design keeps scaling in the canonical domain model rather than in the MuJoCo compiler. Importers can populate `Link.transform`, and backends can consume it, but the scaling logic itself remains backend-neutral.

## 6. Assemblies and Skin Attachments

Assemblies define relationships between systems, while skins define deformable visual/fit layers attached to a system.

- **SystemAssembly**: Collects `AssemblyConnection` and `CoordinateCoupling` definitions.
- **AssemblyEndpoint**: Describes a contextual assembly endpoint by referencing one system's links, sites, and geometries.
- **AssemblyConnection**: Connects one or two `AssemblyEndpoint`s with a relative transform and constraint policy.
- **SkinAttachment**: Associates a deformable mesh or bundle with a `target_system_id` and link-based bindings.
- **SkinAttachmentFit**: Stores registration metadata such as anchor link and reference links/sites/geometries.

New workflows should target `SystemModel`, `SystemAssembly`, and `SkinAttachment` directly.

## 8. Validation Architecture

Validation is a three-pass system that generates a collection of `ValidationIssue` objects. Each issue contains a severity level, an error code, a human-readable message, and a dot-notation path to the invalid data.

1. **Reference Pass (`references.py`)**: Ensures all ID cross-references are resolvable. It checks that joints point to existing frames, muscles point to existing bodies, and sensors point to existing joints.
2. **Topology Pass (`topology.py`)**: Validates the structural integrity. It ensures ID uniqueness across the project, verifies that muscle paths have at least an origin and insertion, and checks for cyclical or self-parenting joints.
3. **Transform Pass (`transforms.py`)**: Performs numerical sanity checks. It verifies that all values are finite, quaternions are normalized, identifiers follow the `[A-Za-z][A-Za-z0-9_.-]*` pattern, and simulation configurations (like timestep) are within valid bounds.

## 9. JSON I/O System

The framework provides a robust serialization layer that handles the translation between Python objects and portable JSON.

- **Serialization**: `project_to_dict(project)` recursively converts dataclasses to dictionaries, transforming enums into their string values. `project_to_json(project)` returns a JSON string.
- **Deserialization**: `project_from_dict(data)` uses type-hint-driven reconstruction. The internal `_structure_dataclass` function handles the instantiation of nested models.
- **File Access**: `save_project` and `load_project` provide high-level wrappers for file I/O.
- **Versioning**: The system tracks `CURRENT_SCHEMA_VERSION` (0.1.0). Deserialization rejects unknown versions with an explicit error.

## 10. Blender Integration Architecture

The Blender integration uses a non-destructive tagging system to map Blender's scene graph to Melos's core models.

- **Tagging**: Objects are identified using `ENTITY_KIND_KEY` ("melos_entity_kind") and `ENTITY_ID_KEY` ("melos_id") stored in Blender's custom properties.
- **Entity Kinds**: The scene still uses entity kinds such as `anatomical_link`, `anatomical_joint`, `device_link`, `muscle_path_point`, and `attachment`, but Blender increasingly maps those UI concepts into canonical `SystemModel` / `SystemAssembly` data.
- **Property Mapping**: Over 70 constants in `constants.py` define the mapping between Blender custom properties and core model fields.
- **I/O Operations**:
  - **bpy_io Builder**: Scans the scene for tagged objects to construct a `Project`.
  - **bpy_io Importer**: Reconstructs a Blender scene from a core model, creating tagged empties and meshes.
- **UI**: Custom operators provide actions for creating tagged entities, while sidebars in the 3D View (under the "melos" tab) expose properties for editing.

## 11. MuJoCo Compiler Architecture

The compiler transforms a `Project` into a valid MJCF XML file and a signal mapping for control.

- **Entry Point**: `compile_project(project, validate=True)` returns a `MujocoCompileResult`.
- **Internal State**: A `_CompilerState` object tracks generated XML elements and name mappings to ensure unique identifiers in the output XML.
- **Compilation Phases**:
    1. Validate project integrity.
    2. Build asset manifest (meshes, materials).
    3. Create the XML root and default settings.
    4. Compile articulated systems using canonical link/joint transforms.
    5. Compile contact geometries and explicit pairs.
    6. Compile sensors, actuators, and muscle-like structures.
    7. Compile assemblies/connections where supported by the backend.
    8. Compile simulation options and keyframes.
    9. Build the signal map for the controller interface.

## 12. Enum Reference Table

| Enum | Values |
| :--- | :--- |
| **JointKind** | `fixed`, `revolute`, `prismatic`, `universal`, `spherical`, `planar`, `free`, `custom` |
| **CoordinateKind** | `rotation`, `translation` |
| **SensorKind** | `position`, `velocity`, `force`, `torque`, `imu`, `contact`, `custom` |
| **ActuatorKind** | `motor`, `torque`, `force`, `position`, `muscle`, `custom` |
| **InterfaceKind** | `cuff`, `footplate`, `harness`, `socket`, `custom` |
| **ContactGeometryKind** | `sphere`, `capsule`, `box`, `cylinder`, `mesh`, `plane` |
| **ContactFilterMode** | `include`, `exclude` |
| **WrapGeometryKind** | `cylinder`, `sphere`, `ellipsoid`, `torus`, `mesh`, `custom` |
| **MusclePathPointKind** | `origin`, `via`, `insertion` |
| **AssetRole** | `imaging`, `segmentation`, `visual`, `collision`, `simulation`, `fitting`, `analysis` |
| **SolverType** | `pgs`, `cg`, `newton` |
| **IntegratorType** | `euler`, `implicit`, `implicitfast`, `rk4` |
| **ValidationSeverity** | `error`, `warning` |

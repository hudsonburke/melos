# MuJoCo Compiler Reference

The melos MuJoCo compiler converts a validated Project into a complete MJCF XML representation for simulation. It maps canonical core entities like systems, links, joints, sites, sensors, and actuators to their MuJoCo equivalents while preserving articulated hierarchy and project semantics.

## Overview

The primary entry point for compilation is the `compile_project` function.

```python
compile_project(
    project: Project,
    *,
    validate: bool = True,
) -> MujocoCompileResult
```

The compiler produces a `MujocoCompileResult` which contains the final MJCF XML string, an asset manifest for external resources, a signal map for control interfaces, and a compilation report.

## Compilation Pipeline

The compiler executes through a series of ordered phases to build the final simulation model:

1.  **Validate project**: Performs structural and logic checks on the Project. Raises `ValueError` if validation fails.
2.  **Build asset manifest**: Selects required assets by role (e.g., collision vs. visual) for inclusion in the simulation.
3.  **Create XML skeleton**: Initializes the `mujoco` root element and configures global compiler settings and default attributes.
4.  **Compile articulated systems**: Builds MJCF body trees from canonical anatomical/device systems, using link transforms as the source of `pos` and `quat`.
5.  **Compile joints**: Maps `JointKind` definitions to MJCF joint elements.
6.  **Compile contact geometries**: Adds `geom` elements for collision detection.
7.  **Compile contact pairs**: Generates `pair` or `exclude` elements in the contact section to manage interactions.
8.  **Compile sensors and actuators**: Emits backend sensor and actuator elements.
9.  **Compile muscles as tendons**: Converts muscle-like structures into `spatial` tendons with ordered site waypoints.
10. **Compile simulation options**: Configures the `option` element with timestep, gravity, solver, and integrator settings.
11. **Compile keyframes**: Creates the `keyframe` element, mapping coordinate names to `qpos` indices.
12. **Add ground plane**: Injects a default ground plane into the worldbody.
13. **Build signal map**: Establishes bindings between observation/command channels and MuJoCo backend components.

## Entity Compilation Mapping

The following table details how core entities translate to MJCF elements.

| Core Entity | MJCF Output | Notes |
|---|---|---|
| Anatomical Link | `<body name="anatomical_link_{id}">` | Includes `pos` and `quat` from `transform`; identity values are omitted. |
| AnatomicalSite | `<site name="{prefix}_frame_{id}">` | Prefix is "anatomical" or the specific `device_id`. |
| AnatomicalJoint REVOLUTE | `<joint type="hinge">` | One element per coordinate; includes axis and range. |
| AnatomicalJoint PRISMATIC | `<joint type="slide">` | One element per coordinate; includes axis and range. |
| AnatomicalJoint FREE | `<freejoint>` | Emitted for the body; no individual coordinates. |
| AnatomicalJoint SPHERICAL | `<joint type="ball">` | No axis or range attributes. |
| AnatomicalJoint UNIVERSAL | 2× `<joint type="hinge">` | One element per coordinate axis. |
| AnatomicalJoint PLANAR | 2× `<joint type="slide">` + 1× `<joint type="hinge">` | Slides on X and Y; rotation on Z. |
| AnatomicalJoint FIXED | Nothing emitted | Results in a static connection between bodies. |
| AnatomicalJoint CUSTOM | Warning | Skipped; not supported by the compiler. |
| ContactGeometry | `<geom name="contact_{id}" type="{kind}">` | Placed directly on the parent body element. |
| ContactPair INCLUDE | `<pair geom1="..." geom2="...">` | Defined within the `contact` section. |
| ContactPair EXCLUDE | `<exclude body1="..." body2="...">` | Defined within the `contact` section. |
| DeviceLink | `<body name="{device_id}_link_{id}">` | Nested under the attachment parent body. |
| DeviceSensor POSITION | `<jointpos joint="...">` | Requires a valid target joint. |
| DeviceSensor VELOCITY | `<jointvel joint="...">` | Requires a valid target joint. |
| DeviceSensor FORCE | `<force site="...">` | References the associated frame site. |
| DeviceSensor TORQUE | `<torque site="...">` | References the associated frame site. |
| DeviceSensor IMU | `<accelerometer>` + `<gyro>` | One core sensor emits two MJCF sensors. |
| DeviceSensor CONTACT | `<touch site="...">` | References the associated frame site. |
| DeviceSensor CUSTOM | Warning | Skipped; not supported by the compiler. |
| DeviceActuator POSITION | `<position joint="..." kp="...">` | Implemented as a position servo. |
| DeviceActuator (other) | `<motor joint="...">` | Generic motor implementation. |
| MuscleModel | `<spatial><site/></spatial>` | Defined in the `tendon` section with waypoints. |
| WrapGeometry cylinder | `<geom type="cylinder">` | Non-colliding (`contype="0"`, `conaffinity="0"`). |
| WrapGeometry sphere | `<geom type="sphere">` | Non-colliding (`contype="0"`, `conaffinity="0"`). |
| WrapGeometry ellipsoid | `<geom type="ellipsoid">` | Non-colliding (`contype="0"`, `conaffinity="0"`). |
| SimulationConfig | `<option>` | Maps timestep, gravity, solver, and integrator. |
| Keyframes | `<key name="..." qpos="...">` | Maps named coordinates to state vector indices. |
| Ground plane | `<geom name="ground">` | Plane type, size "5 5 0.1", rgba "0.8 0.8 0.8 1". |

## Visual Mesh Assets

The compiler supports the emission of complex visual meshes for anatomical bodies. This is particularly used by the `melos-skin` path to provide realistic anatomical appearance.

- **Asset Mapping**: Links that have `AnatomicalLink.asset_ids` referencing assets with `AssetRole.VISUAL` will produce an MJCF `<asset>` section containing `<mesh>` entries for each unique mesh file.
- **Geom Emission**: For each visual asset referenced by a body, a visual-only geom is created as a child of that body: `<geom type="mesh" mesh="..." contype="0" conaffinity="0" group="1"/>`. These geoms do not participate in physics collisions.
- **Unresolved Assets**: If a body references an asset ID that cannot be found in the `AssetLibrary`, the compiler emits a `visual.asset.unresolved` warning but continues compilation without that specific mesh.

## Compiler State

The compiler uses an internal `_CompilerState` dataclass to track mappings and references across different phases:

*   **body_elements**: Maps `(owner, body_id)` to the generated XML Element.
*   **body_names**: Maps `(owner, body_id)` to the MJCF body name string.
*   **joint_names**: Maps `(owner, joint_id)` to the MJCF joint name.
*   **coordinate_joint_names**: Maps `coord_id` to the specific MJCF joint name.
*   **actuator_names**: Maps `actuator_id` to the MJCF actuator name.
*   **frame_transforms**: Maps `frame_id` to its calculated `Transform`.
*   **point_sites**: Maps `point_id` to the MJCF site name.
*   **contact_geom_names**: Maps `contact_geom_id` to the MJCF geom name.
*   **sensor_names**: Maps `sensor_id` to the MJCF sensor name.

## MujocoCompileResult

The compilation process returns a `MujocoCompileResult` object containing:

*   **mjcf_text** (`str`): The full MJCF XML string ready for MuJoCo.
*   **asset_manifest** (`list[AssetBinding]`): A list of assets used, including `asset_id`, `role`, `uri`, and `usage`.
*   **signal_map** (`SignalMap`): Contains `observations: list[SignalBinding]` and `commands: list[SignalBinding]`.
*   **report** (`CompileReport`): A collection of `CompileWarning` objects detailing any issues encountered.

## Signal Map

The `SignalMap` defines how the project's `ControlInterface` channels connect to the underlying MuJoCo simulation:

*   Each `ObservationChannel` has its `source_ref` matched against the `sensor_names` in the compiler state.
*   Each `CommandChannel` has its `target_ref` matched against the `actuator_names` in the compiler state.
*   A `SignalBinding` includes the `signal_id`, `external_name`, `reference`, `backend_type`, and `backend_name`.

## Compile Warnings

The compiler may emit warnings during the process without halting execution. Common warnings include:

*   **CUSTOM joint kind skipped**: Emitted when a joint uses a non-standard kind that the compiler cannot map.
*   **CUSTOM sensor kind skipped**: Emitted when a sensor type is not recognized.
*   **Unresolved signal bindings**: Occurs when a control interface channel cannot be mapped to a generated sensor or actuator.
*   **Unsupported wrap geometry**: Emitted for wrap geometries like torus, mesh, or custom types.

## Assembly and Attachment Compilation

Assembly support is migrating from older attachment-specific models toward canonical `SystemAssembly` / `AssemblyConnection` data. Older attachment-based composition paths may still appear in parts of the repository, but new architecture work targets system-native assembly semantics.

## Scaling Integration

The MuJoCo package works with the scaling pipeline, but scaling itself lives in `melos.core`.

Typical workflow:

1. `load_project(...)` to load a canonical `Project`, or `import_mjcf(...).project` to import one from MJCF (`import_mjcf()` returns `ImportResult`).
2. `scale_model(project, link_vectors, joint_map)` to produce a anatomical-system-specific cloned project.
3. `compile_project(scaled_project)` to emit MJCF for the scaled model.

Important details:

- `import_mjcf()` populates canonical system link transforms from MJCF body transforms.
- The compiler reads canonical link transforms directly when emitting body `pos` and `quat`.
- `link_vectors` passed to `scale_model()` are parent-relative segment vectors, not absolute world positions.
- The compiler does not perform scaling on its own; it lowers whatever canonical project it receives.

## Usage Example

The following example demonstrates loading a project and compiling it for MuJoCo.

```python
from melos.core.io.json import load_project
from melos.sim import compile_project

# Load the project from a JSON definition
project = load_project("my_project.json")

# Compile the project into MJCF
result = compile_project(project)

# Access the generated XML
print(result.mjcf_text)

# Inspect signal bindings for control
for binding in result.signal_map.observations:
    print(f"Observation: {binding.external_name} -> {binding.backend_name}")

# Check for any warnings during compilation
if result.report.warnings:
    for warning in result.report.warnings:
        print(f"Warning [{warning.code}]: {warning.message}")
```

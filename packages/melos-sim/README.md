# melos Sim

`melos-sim` provides the `melos.sim` umbrella package. Its current backend is `melos.sim.mujoco`, which compiles validated `melos.core` `Project` models into MuJoCo MJCF XML.

Scaling is intentionally not implemented here. If you need a subject-specific model, run `melos.core.scaling.scale_model()` first, then compile the resulting `Project`.

## Overview

The compiler translates a complete musculoskeletal model (subject body, skeletal hierarchy, muscles, devices, and assemblies) into MuJoCo's XML-based model format (MJCF). It generates:

- Complete MJCF XML suitable for direct loading into MuJoCo
- A signal map linking ControlInterface channels to MuJoCo sensors and actuators
- An asset manifest tracking which external assets are selected for compilation
- Compile warnings for unsupported features and approximations

## Current Capabilities

**Joint Compilation**:
- Revolute joints (hinge)
- Prismatic joints (slide)
- Free joints (freejoint for floating bodies)
- Spherical joints (ball)
- Universal joints (2x hinge)
- Planar joints (2x slide + hinge)
- Fixed joints (emit nothing)
- Custom joints (generate compile warning)

**Contact Compilation**:
- Contact geometries as geoms attached to bodies
- Contact pairs as pair/exclude elements

**Sensor Compilation**:
- Position sensors (jointpos)
- Velocity sensors (jointvel)
- Force and torque sensors
- IMU sensors (accelerometer + gyro)
- Contact sensors (touch)
- Custom sensors (generate compile warning)

**Actuator Compilation**:
- Position actuators (position servo)
- All other actuator types (motor)

**Muscle and Tendon Compilation**:
- Spatial tendons with ordered site waypoints
- Wrap geometry support: cylinder, sphere, ellipsoid (compiled as non-colliding geoms with contype="0")

**Simulation Configuration**:
- Timestep and gravity
- Solver selection (pgs, cg, newton)
- Integrator selection (euler, implicit, implicitfast, rk4)
- Solver iterations and tolerance

**Additional Features**:
- Keyframe compilation mapping coordinate names to qpos indices
- Signal map generation linking ControlInterface channels to MuJoCo sensors/actuators
- Asset manifest tracking selected assets for compilation
- Ground plane (always present)
- Compile warnings for unsupported features

## Architecture

**Core Modules**:

- `compiler/mjcf.py`: Main compiler (~1100 lines), provides `compile_project` entry point
- `compiler/attachments.py`: Device attachment transform resolution
- `compiler/muscles.py`: Muscle/tendon site sequence building
- `compiler/assets.py`: Asset manifest construction
- `importers/`: MJCF import support that reconstructs canonical `melos.core` models, including `SubjectBody.transform`
- `reports.py`: CompileWarning, CompileReport, AssetBinding, SignalBinding, SignalMap, MujocoCompileResult

## Usage

```python
from melos.core.io.json import load_project
from melos.core.scaling import scale_model
from melos.sim import compile_project

project = load_project("my_project.json")
scaled = scale_model(
    project,
    subject_joints={"r_elbow_flex": (0.0, 0.0, 0.45)},
    joint_map={"r_elbow_flex": "r_ulna_radius_hand"},
)
result = compile_project(scaled)

# Access the compiled MJCF XML
with open("model.xml", "w") as f:
    f.write(result.mjcf_text)

# Access signal map for control
for binding in result.signal_map.observations:
    print(f"{binding.signal_id} -> {binding.backend_name}")
```

## Dependencies

- `melos-core` (only external dependency)
- Python standard library (`xml.etree` for XML generation)
- No MuJoCo Python package required

## Documentation

See `docs/mujoco-compiler.md` for complete compilation mapping reference, including how `SubjectBody.transform` and the core scaling pipeline fit into the import → scale → compile workflow.

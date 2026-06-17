# melos — Subject-specific musculoskeletal modeling, exoskeleton design, and simulation

## Overview

melos is a framework for subject-specific musculoskeletal modeling, assistive device design, and physics simulation. It provides a unified data model for describing biological subjects (bones, joints, muscles), wearable devices (exoskeletons, prosthetics), and the assembly between them.

The framework is structured as a monorepo with four primary namespace packages that handle the canonical data model, skin/model pipelining, visual authoring, and simulation compilation. The canonical core architecture is now system-centric: `Project` contains `systems`, `assemblies`, and optional `skin_attachments`, while Blender, MuJoCo, and skin adapters translate to and from that shared representation.

## Architecture

The framework consists of four namespace packages under `melos.*`, each residing under `packages/`:

*   **`melos.core` (`packages/melos-core/`)**
    The foundation of the framework. It contains pure Python domain models, validation logic, JSON I/O, and subject-specific model scaling. This package defines the canonical `Project` schema and has no dependencies on Blender or MuJoCo.
*   **`melos.skin` (`packages/melos-skin/`)**
    A subject-specific pipeline package. Converts GEM/SOMA-X outputs into a canonical `melos.core.Project`, scaled to real human proportions, with per-body visual mesh assets. Optional GEM video ingestion via subprocess. Keep all heavy ML dependencies (numpy, torch, trimesh) here; `melos-core` stays pure Python.
*   **`melos.blender` (`packages/melos-blender/`)**
    A Blender addon for visual authoring. It provides operators, panels, and builders to create and manipulate models within the Blender scene. It handles scene tagging and the mapping between Blender objects and the melos domain models.
*   **`melos.sim.mujoco` (`packages/melos-sim/`)**
    The simulation compiler. It converts a validated `Project` instance into MuJoCo-compatible MJCF XML, along with a signal map for control and an asset manifest for external resources.

## Data Flow

The following diagram illustrates the data flow between the different components:

```text
Visual Authoring (Blender)           Domain Model (Core)                    Simulation (MuJoCo)
--------------------------           -------------------                    -------------------

+------------------+                 +------------------+    scale_model    +------------------+
|                  |    bpy_io       |                  | ----------------> |  Scaled Project   |
|  Blender Scene   | --------------> |  Project         |                   |                  |
|                  |                 |                  | <---------------- +------------------+
+------------------+                 +------------------+      import               |
        ^                                    |     ^                                 | compile
        |                                    |     |                                 v
        |            importer                |     |                         +------------------+
        +------------------------------------+     |                         |                  |
                                             |     |                         |  MJCF XML        |
                                             v     |                         |                  |
                                     +------------------+                    +------------------+
                                     |                  |                            |
                                     |  JSON Storage    |                            v
                                     |                  |                    +------------------+
                                     +------------------+                    |  Signal Map      |
                                                                               |                  |
                                                                               +------------------+
```

## The Project Model

The `Project` is the root aggregate of the framework, defined in `melos.core.project.model`. It contains:

*   **ProjectMeta**: Metadata including schema versioning (current 0.1.0).
*   **AssetLibrary**: Definitions of meshes and textures used across the project.
*   **systems: list[SystemModel]**: Canonical articulated systems. A subject, device, or other articulated asset is represented as a `SystemModel` with links, joints, sites, geometries, actuators, sensors, and interfaces.
*   **assemblies: list[SystemAssembly]**: Interface-centric connections and coordinate couplings between systems.
*   **skin_attachments**: Optional deformable skin layers attached to a target system using link-based bindings.
*   **translation_maps**: Optional semantic mappings used by retargeting/alignment workflows.
*   **SimulationConfig**: Global simulation parameters such as solver, integrator, timestep, gravity, and keyframes.
*   **ControlInterface**: Definitions for observations (sensor outputs) and commands (actuator inputs).

`Project`, `SystemModel`, `SystemAssembly`, and system-aware `SkinAttachment` are the supported architectural foundation.

## Key Design Principles

*   **Thin layer**: melos is an authoring and translation tool, not a second simulator. It delegates physics to established backends like MuJoCo.
*   **Explicit SI units**: All values (meters, kilograms, seconds, radians) are in SI units. Scaling produces a new `Project`; serialization stays in canonical SI units.
*   **Frame-first modeling**: All components are defined relative to frames, allowing for complex hierarchical transformations and stable local coordinates.
*   **Stable IDs**: Internal identifiers are separate from display names, ensuring that renaming objects in the UI does not break data relationships.
*   **Backend-neutral semantics**: While the initial implementation is biased toward MuJoCo, the core model remains independent of simulation engine specifics.
*   **Pure Python core**: The `melos.core` package has zero dependencies on Blender (`bpy`) or MuJoCo (`mujoco`), making it suitable for server-side processing or standalone scripts.
*   **Typed data structures**: All domain models use typed dataclasses with `slots=True` and `kw_only=True`. Enums are `StrEnum` with lowercase values.
*   **Versioned serializable project model**: The model is designed for round-trip JSON serialization with schema versioning for long-term compatibility.

## Quick Start

### Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and sync
git clone <repo-url> && cd melos
uv sync              # installs melos-core + melos-sim + dev tools
uv sync --all-packages  # also installs melos-skin + melos-blender
```

### Running Tests

Default (fast, safe subset):

```bash
uv run pytest
```

Full suite across every package:

```bash
uv run pytest packages/melos-core/tests packages/melos-sim \
  packages/melos-skin/tests packages/melos-blender/tests
```

Some tests are opt-in and skip automatically when their heavy backends are
absent: MHR/skin tests need `melos-skin[mhr]` (`py-soma-x`, torch), and the
high-fidelity MJCF import test needs `melos-sim[mjcf-import]` (`dm_control`).
The compiler and the stdlib MJCF importer fallback need neither.

### Basic Usage

```python
from melos.core.io.json import load_project, save_project
from melos.core.scaling import scale_model
from melos.core.validation import validate_project
from melos.sim import compile_project

# 1. Load an existing project
project = load_project("my_project.json")

# 2. Optionally scale a generic template to a subject-specific project
subject_joints = {
    "r_elbow_flex": (0.0, 0.0, 0.45),
}
joint_map = {
    "r_elbow_flex": "r_ulna_radius_hand",
}
project = scale_model(project, subject_joints, joint_map)

# 3. Validate the project
report = validate_project(project)
if report.has_errors:
    for issue in report.issues:
        print(f"[{issue.severity}] {issue.location}: {issue.message}")

# 4. Compile to MuJoCo MJCF
result = compile_project(project)

with open("model.xml", "w") as f:
    f.write(result.mjcf_text)

# 5. Use the signal map for control
for binding in result.signal_map.observations:
    print(f"Observation: {binding.signal_id} -> {binding.backend_name}")
```

`scale_model()` lives in `melos.core` and returns a new `Project`. It expects `subject_joints` to contain parent-relative segment vectors keyed by joint name, and `joint_map` to map those joint names to child link IDs in the subject system. Links not listed in `joint_map` inherit the nearest ancestor scale.

## Project Structure

```text
melos/
├── packages/
│   ├── melos-core/                      # melos.core package
│   │   ├── src/melos/core/
│   │   ├── common/                      # Types, IDs, enums, units, transforms
│   │   ├── project/                     # Project aggregate
│   │   ├── system/                      # Canonical systems, interfaces, assemblies
│   │   ├── retarget/                    # Canonical retarget joints and measurements
│   │   ├── subject/                     # Legacy subject-specific models still used in some paths
│   │   │   └── muscles/                 # Muscle models, wraps, physiology
│   │   ├── device/                      # Legacy device-specific models
│   │   ├── assembly/                    # Legacy attachment/coupling models
│   │   ├── contact/                     # Contact geometries, collision pairs
│   │   ├── simulation/                  # Solver, integrator, keyframes
│   │   ├── control/                     # Observation/command channels
│   │   ├── assets/                      # Asset library and records
│   │   ├── validation/                  # References, topology, transforms
│   │   ├── scaling/                     # Subject-specific model scaling pipeline
│   │   └── io/                          # JSON serialization, schema, migrations
│   │   └── tests/                       # Core test suite
│   ├── melos-skin/                      # melos.skin package
│   │   ├── src/melos/skin/
│   │   ├── adapters/                    # MHR/runtime-backed skin bundle loaders
│   │   ├── mappings/                    # Human retarget/translation maps
│   │   └── tests/                       # Skin pipeline tests
│   ├── melos-blender/                   # melos.blender package
│   │   └── src/melos/blender/
│       ├── addon/
│       │   ├── operators/               # UI operators (subject, device, muscle, etc.)
│       │   └── panels/                  # Sidebar panels (melos tab)
│   │       ├── bpy_io/                  # Scene ↔ core model builders + importer
│   │       └── services/                # Pure Python helpers (IDs, validation)
│   └── melos-sim/                       # melos.sim package (MuJoCo backend today)
│       └── src/melos/sim/
│           ├── __init__.py              # Convenience re-exports for the default backend
│           └── mujoco/
│               ├── compiler/            # MJCF generation (mjcf.py, attachments, muscles, assets)
│               └── reports.py           # MujocoCompileResult, SignalMap, CompileWarning
├── resources/                           # Pinned runtime assets used by examples and packaging
│   └── third_party/
│       ├── myofullbody/
│       └── skin/
└── docs/                                # Documentation
```

## Current Status (v0.1)

*   **Core**: Canonical system-centric domain model with `SystemModel`, `SystemAssembly`, retarget/measurement helpers, simulation/control/assets, validation, and JSON I/O. Includes `melos.core.scaling.scale_model()` for subject-system scaling.
*   **Skin Pipeline**: First-party supported skin/model-provider path under `melos.skin`, currently centered on MHR-backed skin bundles and human retarget mappings.
*   **Blender**: Authoring and visualization support. Blender increasingly acts as a frontend over core-native systems, assemblies, and skin attachments rather than owning domain semantics itself.
*   **MuJoCo**: MJCF compilation support for system-based projects, including joints, contacts, sensors, actuators, muscles/tendons, simulation options, keyframes, and automatic signal map generation.
*   **Tests**: The default test surface is intentionally narrow and safe; broad runs remain opt-in because some skin/runtime integration tests are heavy.

## Documentation

For more detailed information, see the files in the `docs/` directory:

*   `architecture.md`: High-level system design.
*   `core-api-reference.md`: API documentation for the core domain model, including the scaling pipeline.
*   `core-developer-guide.md`: Contributor guide for extending `melos.core` models, validation, JSON I/O, and scaling.
*   `mujoco-compiler.md`: Details on the MJCF translation process.
*   `blender-addon-guide.md`: User guide for the Blender authoring environment.
*   `blender-developer-guide.md`: Contributor guide for addon operators, panels, scene tagging, bpy_io builders, importers, and fake-bpy tests.
*   `developer-guide.md`: Contribution guidelines and development workflow.
*   `workflow-guide.md`: End-to-end tutorial from modeling to simulation, including subject-specific scaling.

## Namespace Strategy

melos uses PEP 420 namespace packages. There is no shared `__init__.py` file in the `melos/` directory within any package. This allows each package (`core`, `blender`, `skin`, `sim`) to be installed independently and maintained as a separate codebase while appearing under the same logical `melos` namespace.

## License

See LICENSE for more information.

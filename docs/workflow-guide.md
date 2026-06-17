# Workflow Guide

This guide covers the end-to-end workflow for musculoskeletal modeling, skin fitting, cable-driven exoskeleton design, and MuJoCo simulation.

## Overview

The pipeline has two modes:

1. **Headless (Python script)** — import MJCF, add cable devices, compile to MJCF. No Blender required.
2. **Blender authoring** — visualize the model, fit skin meshes, pose the rig, place cable routing points interactively, then export.

Both paths converge on the same `melos.core.Project` data model and produce MuJoCo MJCF output.

## Prerequisites

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and sync the workspace
git clone <repo-url> && cd melos
uv sync              # installs melos-core + melos-sim
uv sync --all-packages  # also installs melos-skin + melos-blender
```

Third-party assets must be extracted to `resources/third_party/`:
- `resources/third_party/myofullbody/` — MyoFullBody MuJoCo model (101 links, 424 muscles)
- `resources/third_party/skin/` — SOMA-X neutral registration + MHR model

## Headless Workflow

Run the complete import → cable → compile pipeline without Blender:

```bash
uv run python scripts/exoskeleton_cable_workflow.py
```

This script:
1. Imports the MyoFullBody MJCF model into a `melos.core.Project`
2. Builds a cable-driven knee-assist exoskeleton device with:
   - Hip anchor link attached to pelvis
   - Knee pulley wrap geometry on the thigh cuff
   - Cable running: pelvis anchor → knee pulley wrap → tibia insertion
   - Motor actuator driving the cable tendon
3. Compiles to MuJoCo MJCF with spatial tendons + motor actuators
4. Saves both MJCF and project JSON

Output:
- `output/exoskeleton_model.xml` — MuJoCo MJCF with 101 anatomical links, 424 muscles, and 1 cable tendon
- `output/exoskeleton_project.json` — Portable project JSON

### With Skin Fitting

```bash
uv run python scripts/exoskeleton_cable_workflow.py --with-skin
```

Requires the MHR runtime (`py-soma-x`, `torch`). Generates a skinned body mesh OBJ and attaches skin metadata to the project.

## Blender Workflow

### Step 1: Install the Addon

Build and install the Blender addon:

```bash
uv run python packages/melos-blender/scripts/build_blender_addon.py --output-dir dist
```

In Blender: Edit → Preferences → Add-ons → Install → select `dist/melos-addon-0.1.0.zip`.

### Step 2: Import or Create the Model

**Option A: Import existing project JSON**
1. Open the Sidebar (N key) → melos tab → Project panel
2. Click "Import Project" → select `exoskeleton_project.json`
3. The full anatomical + device model appears in the scene

**Option B: Create from scratch using the example workflow**
1. In the melos tab → Project panel, click "Create Example Project"
2. This imports the MyoFullBody model, fits the MHR skin, creates an armature, and adds a cable device

### Step 3: Visualize the MyoFullBody Model

The import creates:
- **Tagged empties** for each anatomical link, joint, site, and geometry
- **An armature** (`myofullbody_armature`) with bones matching the MuJoCo link hierarchy
- **A skinned mesh** (`myofullbody_skin`) with vertex weights from the MHR model
- **Body mesh references** showing bone geometry for visual context

The armature uses stick display and the skin mesh uses a semi-transparent material.

### Step 4: Fit the Skin Mesh (MHR / SOMA-X)

The skin fitting pipeline:
1. Loads the MHR model via `py-soma-x` runtime
2. Generates a neutral-pose body mesh (vertices + faces)
3. Aligns the mesh to the MuJoCo skeleton using Kabsch SVD alignment
4. Collapses joint weights to link weights for Blender's armature modifier
5. Creates a skinned mesh with the armature

Skin fitting is automatic when using "Create Example Project". For manual fitting:

```python
from melos.skin.adapters import build_example_mhr_skin_bundle
skin_bundle = build_example_mhr_skin_bundle("resources/third_party/skin")
```

### Step 5: Pose the Rigged Model

The armature is fully poseable:
1. Select the armature in Pose Mode
2. Rotate bones to pose the model
3. The skin mesh deforms via the armature modifier
4. Body mesh references follow the pose

### Step 6: Place Cable Routing Points

Cable routing defines the path of cables for a cable-driven exoskeleton:

1. In the melos tab → Device panel, configure the device ID and name
2. Create device links (anchor points on the exoskeleton frame)
3. Create device joints (connections between frame segments)
4. Click "Create Cable Route Point" to place route waypoints:
   - **Actuator ID**: Which cable actuator this point belongs to
   - **Order**: Sequence number (0, 1, 2, ...) defining cable path order
   - **Node Kind**: `site` (passes through a point) or `wrap` (wraps around geometry)
   - **Site ID / Geometry ID**: Reference to the anatomical site or wrap geometry
5. Repeat for each waypoint along the cable path
6. Click "Update Cable Visualization" to see the cable path as a Bezier curve

Cable route points are stored as tagged empties with `melos_entity_kind = "device_cable_route_point"`.

### Step 7: Export to MuJoCo

1. In the melos tab → Project panel, click "Export Project JSON"
2. The scene is scanned for tagged objects and compiled into a `Project`
3. Use the headless compiler to generate MJCF:

```python
from melos.core.io.json import load_project
from melos.sim import compile_project

project = load_project("exported_project.json")
result = compile_project(project)
with open("model.xml", "w") as f:
    f.write(result.mjcf_text)
```

### Step 8: Simulate in MuJoCo

```bash
uv run python -m mujoco.viewer --mjcf=model.xml
```

The MJCF contains:
- Full anatomical skeleton with Hill-type muscles as spatial tendons
- Cable-driven exoskeleton as spatial tendons + motor actuators
- Contact pairs for self-collision
- Ground plane

## Cable-Driven Exoskeleton Design

### Architecture

A cable-driven exoskeleton consists of:

1. **Device System** (`SystemRole.DEVICE`): Rigid frame links connected by joints
2. **Wrap Geometries**: Pulleys/guides that redirect cable paths (sphere, cylinder, ellipsoid)
3. **Cable Actuators** (`ActuatorKind.CABLE`): Route through sites and wrap geometries
4. **Motor Actuators** (`ActuatorKind.MOTOR`): Drive the cable tendons with force control
5. **Assembly**: Connects the device to the anatomical system at attachment points

### Cable Route Nodes

Each cable has an ordered list of route nodes:

| Node Kind | Description | MuJoCo Output |
|-----------|-------------|---------------|
| `site` | Cable passes through a point | `<site>` element in spatial tendon |
| `wrap` | Cable wraps around geometry | `<geom>` element in spatial tendon |

### Cable Parameters

| Parameter | Description | MuJoCo Equivalent |
|-----------|-------------|-------------------|
| `stiffness` | Tendon stiffness (N/m) | `stiffness` attribute |
| `damping` | Tendon damping (N·s/m) | `damping` attribute |
| `rest_length` | Rest length (m) | `springlength` attribute |
| `width` | Visual width (m) | `width` attribute |
| `length_range` | Length limits | `range` + `limited` attributes |

## Data Flow Summary

```
MyoFullBody MJCF
       │
       ▼
  import_mjcf()  ──►  Project (anatomical system)
       │
       ├──► build_knee_assist_exoskeleton()  ──►  Project (+ device system)
       │
       ├──► build_example_mhr_skin_bundle()  ──►  Project (+ skin attachment)
       │
       └──► compile_project()  ──►  MJCF XML
              │
              ├──► Spatial tendons (muscles + cables)
              ├──► Motor/muscle actuators
              ├──► Sensors + signal map
              └──► Keyframes + simulation config
```

## Troubleshooting

### "MHR skin runtime is not available"
Install the MHR extras: `uv sync --extra mhr` (requires `py-soma-x` and `torch`)

### "Include file not found" during MJCF import
Ensure `resources/third_party/myofullbody/` contains all sub-directories (body, torso, arm, leg, head, meshes, scene).

### Cable tendon not appearing in MJCF
- Verify the cable actuator has `kind=ActuatorKind.CABLE`
- Verify route nodes reference valid site IDs on the anatomical system
- Verify wrap geometries use `role=GeometryRole.WRAP` (not `COLLISION`)
- Check compile warnings for unresolved site/geometry references

### Custom joint warnings
The MyoFullBody model uses compound joints (translation + rotation). These are compiled as multiple MuJoCo joint elements per body, which is correct behavior.

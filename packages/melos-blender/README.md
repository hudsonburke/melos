# melos Blender

`melos-blender` provides the `melos.blender` package and a Blender add-on entrypoint for authoring canonical `melos.core` models inside Blender.

## Design Principles

- keep `melos.core` as the single source of truth
- provide Blender operators and panels for creating `melos.core` entities
- reconstruct a validated `Project` directly from Blender scene state
- minimize intermediate scene schemas and backend-specific assumptions

## Current Workflow

The add-on supports a complete authoring pipeline:

**Subject Authoring:**
- body creation and geometry registration
- frame creation with transforms
- joint creation with coordinates
- landmark creation

**Device Authoring:**
- link creation and geometry registration
- frame creation with transforms
- joint creation with coordinates
- sensor creation (IMU, contact)
- actuator creation

**Muscle Authoring:**
- muscle path definition (origin, via points, insertion)
- wrap geometry attachment

**Assembly:**
- attachment creation to connect device to subject

**I/O and Validation:**
- JSON export via `melos.core.io.json.save_project()`
- JSON import from file into Blender scene via `import_project_to_scene()`
- validation through `melos.core.validation.validate_project()`
- JSON-first handoff to downstream steps such as scaling and MuJoCo compilation

## Roadmap Direction

The Blender workflow enables subject-specific, geometry-first modeling:

- import subject geometry such as bones, segmentations, and muscle volumes
- import a prior model such as Rajagopal/OpenSim as a starting template
- adapt that template into a canonical `melos.core` project
- optionally scale that canonical project with `melos.core.scaling.scale_model()` using external joint measurements
- place subject-specific muscles, sensors, and actuators in Blender
- validate and export the final project for backend compilation

Recent completions:
- geometry-backed body authoring and asset registration
- explicit frames and joints on top of those bodies
- JSON import/export workflow
- documented JSON → scale → MuJoCo compilation pipeline

Future priorities:
- structure-first template import from OpenSim/Rajagopal
- subject-specific adaptation workflows
- geometry-backed muscle authoring from imported muscle meshes

## Packaged Blender Addon

The repository now includes a packaging workflow for a Blender-installable add-on zip.

Build it locally from the repository root:

```bash
python3 packages/melos-blender/scripts/build_blender_addon.py --output-dir dist
```

This produces a self-contained zip such as `dist/melos-addon-0.1.0.zip` that can be installed through Blender's **Edit → Preferences → Add-ons → Install...** flow.

The packaged addon bundles:

- `melos.blender`
- `melos.core`
- the minimal `melos.skin` modules and resources needed by the Blender UI

There is also a GitHub Actions workflow at `.github/workflows/package-blender-addon.yml` that runs the packaging tests and uploads the zip as a workflow artifact.

## Architecture

- `melos.core` remains the canonical schema and stays pure Python
- `melos.core.scaling` is the canonical place for subject-specific model adaptation
- `melos.blender.addon` is the Blender-facing UI layer
- `melos.blender.bpy_io` reads Blender scene state directly into `melos.core` models, including the importer for JSON project files
- `melos.blender.services` contains pure-Python helpers used by the add-on

## Getting Started

See repository-root `docs/blender-addon-guide.md` for addon setup and authoring reference. See `docs/blender-developer-guide.md` for implementation patterns around operators, panels, `bpy_io`, and fake-bpy tests.

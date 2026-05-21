# Blender Addon Reference Guide

This guide documents the melos.blender addon, a tool for visually authoring melos projects within Blender.

## 1. Overview

The melos.blender addon serves as a visual authoring layer for the melos.core modeling framework. It allows researchers and developers to define biomechanical anatomicals, robotic devices, muscle paths, and complex assemblies using Blender's native 3D environment.

### Architecture

The addon follows a layered architecture to separate UI logic from model construction:

* **addon/**: The UI layer containing Blender-specific operators, panels, and property definitions.
* **bpy_io/**: The translation layer. It contains builders that transform Blender scene state into core models, and importers that reconstruct scene objects from core model files.
* **services/**: Pure Python helper modules that perform logic independent of the Blender API.

The core workflow revolves around reconstructing a `Project` from the Blender scene state on every export operation. In the current architecture, Blender increasingly acts as a frontend over canonical core `SystemModel` / `SystemAssembly` data rather than as the owner of domain semantics. Anatomical-system-specific scaling is a separate pure-Python step in `melos.core`; the Blender addon authors and imports canonical projects, then you can scale those projects programmatically before MuJoCo compilation.

## 2. Installation & Setup

### Developer Workflow

To set up the development environment, install the core and blender packages in editable mode from the repository root:

```bash
python3 -m pip install -e ./packages/melos-core
python3 -m pip install -e ./packages/melos-blender
```

### Loading in Blender

The addon requires the `MELOS_REPO_ROOT` environment variable to be set to the root of the repository. To load the addon for development:

1. Open Blender.
2. In the Scripting tab, use a reload script (for example from `packages/melos-core/scripts/blender-dev-reload.py`, if present in your local workflow) to add the `src/` paths to `sys.path`.
3. Import and register `melos.blender.addon`.

Once registered, the UI appears in the 3D View sidebar (press 'N') under the "melos" tab.

### Packaged Addon Workflow

If you want a Blender-installable zip instead of the development reload flow, build it from the repository root:

```bash
python3 packages/melos-blender/scripts/build_blender_addon.py --output-dir dist
```

This produces `dist/melos-addon-<version>.zip`. Install that file in Blender through **Edit → Preferences → Add-ons → Install...**.

The zip is self-contained for the current UI surface. It bundles `melos.blender`, `melos.core`, and the minimal `melos.skin` modules and resources used by the example-project workflow.

For CI packaging, use `.github/workflows/package-blender-addon.yml`, which runs the packaging tests and uploads the zip as a workflow artifact.

## 3. Scene Tagging System

The tagging system is the fundamental concept of the melos addon. Every melos entity in a Blender scene is a tagged object, typically an Empty.

### Mandatory Tags

Every entity must have two mandatory custom properties:

* `melos_entity_kind` (ENTITY_KIND_KEY): Defines the type of entity.
* `melos_id` (ENTITY_ID_KEY): A stable, unique identifier for the entity.

### Entity Kinds

The addon recognizes a fixed set of entity kinds. Many still use body/device terminology in the UI, but export/import increasingly translates them into canonical system-native core models:

* `anatomical_link`: A rigid body in the anatomical model.
* `anatomical_site`: A coordinate frame attached to a body.
* `anatomical_joint`: A joint connecting two frames.
* `anatomical_link_asset`: A mesh object providing visual or collision geometry for a body.
* `device_link`: A rigid link in a device model.
* `device_frame`: A coordinate frame attached to a link.
* `device_joint`: A joint connecting two device frames.
* `device_sensor`: A sensor attached to a device.
* `device_actuator`: An actuator driving a device joint.
* `device_interface`: A communication interface for the device.
* `muscle_path_point`: A point (origin, insertion, or way-point) in a muscle path.
* `muscle_wrap_geometry`: A geometry primitive for muscle wrapping.
* `attachment`: A constraint connecting a device link to a anatomical body.
* `landmark`: A named spatial reference point on a body.

### Property Constants

Entity properties are stored as custom properties on Blender objects. There are over 70 constants defined in `constants.py`. Key examples include:

* **Bodies**: `BODY_MASS_KEY`, `BODY_CENTER_OF_MASS_KEY`, `BODY_INERTIA_KEY`
* **Frames**: `FRAME_BODY_ID_KEY`, `FRAME_IS_ANATOMICAL_KEY`
* **Joints**: `JOINT_KIND_KEY`, `JOINT_PARENT_BODY_ID_KEY`, `JOINT_CHILD_BODY_ID_KEY`, `JOINT_PARENT_FRAME_ID_KEY`, `JOINT_CHILD_FRAME_ID_KEY`
* **Sensors**: `DEVICE_SENSOR_KIND_KEY`, `DEVICE_SENSOR_FRAME_ID_KEY`, `DEVICE_SENSOR_LINK_ID_KEY`
* **Muscles**: `MUSCLE_ID_KEY`, `MUSCLE_PATH_POINT_KIND_KEY`, `MUSCLE_PATH_POINT_BODY_ID_KEY`

Object names in Blender are treated as display labels. The canonical, stable IDs used by the core models are stored exclusively in the `melos_id` custom property.

## 4. Operators Reference

### Anatomical System Operators

`addon/operators/anatomical.py`

* **MELOS_OT_create_anatomical_link**: Creates an Empty tagged as `anatomical_link`.
* **MELOS_OT_create_body_from_selected_mesh**: Creates a body Empty and automatically tags the active mesh as its `anatomical_link_asset`.
* **MELOS_OT_create_anatomical_site**: Creates an Empty tagged as `anatomical_site`.
* **MELOS_OT_create_anatomical_joint**: Creates an Empty tagged as `anatomical_joint` with coordinate properties.
* **MELOS_OT_assign_selected_mesh_to_body**: Tags an existing mesh as an asset for a specific body ID.
* **MELOS_OT_set_selected_mesh_asset_role**: Changes the asset role (e.g., visual vs collision) on a tagged mesh.

### Device Operators

`addon/operators/device.py`

* **MELOS_OT_create_device_link**: Creates an Empty tagged as `device_link`.
* **MELOS_OT_create_device_frame**: Creates an Empty tagged as `device_frame`.
* **MELOS_OT_create_device_joint**: Creates an Empty tagged as `device_joint`.
* **MELOS_OT_create_device_sensor**: Creates an Empty tagged as `device_sensor`.
* **MELOS_OT_create_device_actuator**: Creates an Empty tagged as `device_actuator`.

### Muscle Operators

`addon/operators/muscle.py`

* **MELOS_OT_create_muscle_path_point**: Creates an Empty tagged as `muscle_path_point`.
* **MELOS_OT_create_wrap_geometry**: Creates an Empty tagged as `muscle_wrap_geometry`.

### Assembly Operators

`addon/operators/assembly.py`

* **MELOS_OT_create_attachment**: Creates an Empty tagged as `attachment` to link devices to anatomicals.

### Landmark Operators

`addon/operators/landmark.py`

* **MELOS_OT_create_landmark**: Creates an Empty tagged as `landmark`.

### Project Operators

`addon/operators/project.py`

* **MELOS_OT_validate_project**: Builds a project from the scene and runs `melos.core.validation.validate_project`.
* **MELOS_OT_export_project_json**: Builds a project from the scene, runs validation, and saves it as a JSON file.

### Import Operator

`addon/operators/importer.py`

* **MELOS_OT_import_project**: Loads a melos JSON project file and reconstructs the tagged Blender objects.

## 5. Panels Reference

The melos tab in the sidebar contains several panels for data entry and operator access:

* **Project Panel**: Contains global project metadata (ID, name, description, created_by), simulation settings (time_step, gravity), and the export path. Includes buttons for export and validation.
* **Anatomical System Panel**: Fields for defining anatomical-level data (ID, name, species) and tools for creating bodies, frames, and joints.
* **Device Panel**: Fields for device ID and name. Tools for creating device links, frames, joints, sensors, and actuators.
* **Muscle Panel**: Fields for muscle ID. Tools for creating muscle path points and wrap geometries.
* **Assembly Panel**: Tools for creating attachments, specifying the `device_id`, `interface_id`, and `anatomical_site_id`.
* **Landmark Panel**: Tools for creating landmarks, including name, target body ID, and description.

## 6. bpy_io Builders

The `bpy_io` module contains logic for extracting data from the Blender scene:

* **Anatomical System/device builders**: Scan tagged scene objects and translate them into core-native system data.
* **Muscle/landmark/asset builders**: Scan `muscle_path_point`, landmark, and mesh asset entities and attach that information to the exported project.
* **Assembly builders**: Scan `attachment` entities and translate them into assembly data.
* **build_project_from_scene(scene) -> Project**: The master builder that orchestrates all sub-builders to produce a complete project model. Settings are read from the scene internally.
* **import_project_to_scene(project, scene, settings) -> list**: The reverse process; it takes a `Project` and instantiates tagged objects in the Blender scene, returning a list of created objects.

## 7. Import Workflow

The process of loading a melos project into Blender follows these steps:

1. The user invokes `MELOS_OT_import_project` and selects a JSON file.
2. The JSON is deserialized into a `Project` object (via `load_project`).
3. The `import_project_to_scene` function is called.
4. For every entity in the project (bodies, frames, joints, landmarks, etc.), a corresponding Empty or Mesh object is created in Blender.
5. Mandatory tags (`melos_entity_kind` and `melos_id`) are applied to each object.
6. Additional custom properties are populated from the core model fields.
7. Objects are named using a convention of `[Kind]_[ID]` for human readability.

## 8. Export Workflow

The export workflow ensures that the visual scene is converted into a valid simulation model:

### Save Project (JSON)

1. User clicks "Export Project JSON".
2. `build_project_from_scene` traverses the scene and builds the `Project` object.
3. Validation is performed on the constructed object.
4. If valid, the project is serialized to JSON at the specified export path.

### Export MuJoCo (MJCF)

MuJoCo export is not yet available as a Blender operator. Export the project as JSON first, optionally run `melos.core.scaling.scale_model()` if you need anatomical-system-specific adaptation from external joint data, and then use `melos.sim.mujoco.compile_project` from Python (see the Workflow Guide).

If your scaling input comes from an external source such as marker-based joint extraction, SOMA-X, or another fitting pipeline, convert that data into parent-relative segment vectors and pass it to `scale_model()` together with a joint-to-link map.

## 9. Addon Properties

The `MELOSAddonSettings` class contains approximately 65 properties that store scene-level configuration. These properties are accessible via `context.scene.melos_settings`.

* **Project**: `project_id`, `project_name`, `project_description`, `created_by`.
* **Anatomical System**: `anatomical_id`, `anatomical_name`, `anatomical_description`, `anatomical_species`, `anatomical_root_link_id`.
* **Simulation**: `time_step`, `duration`, `gravity_x`, `gravity_y`, `gravity_z`.
* **Authoring Fields**:
  * Bodies: `new_body_name`, `new_body_id`, `mesh_asset_role`, `mesh_target_link_id`.
  * Frames: `new_frame_name`, `new_frame_id`, `frame_body_id`, `frame_is_anatomical`.
  * Joints: `new_joint_name`, `new_joint_id`, `joint_kind`, `joint_parent_frame_id`, `joint_child_frame_id`, `joint_parent_link_id`, `joint_child_link_id`.
  * Coordinates: `coordinate_name`, `coordinate_id`, `coordinate_kind`, `coordinate_axis_x/y/z`, `coordinate_default_value`.
* **Device Fields**: `device_id`, `device_name`, `device_root_link_id`, `new_device_link_name`, `new_device_link_id`, `new_device_frame_name`, `new_device_frame_id`, `device_frame_link_id`.
  * Device Joints: `new_device_joint_name`, `new_device_joint_id`, `device_joint_kind`, `device_joint_parent_link_id`, `device_joint_child_link_id`, `device_joint_parent_frame_id`, `device_joint_child_frame_id`.
  * Device Coordinates: `device_coordinate_name`, `device_coordinate_id`, `device_coordinate_kind`, `device_coordinate_axis_x/y/z`.
  * Sensors: `new_device_sensor_name`, `new_device_sensor_id`, `device_sensor_kind`, `device_sensor_frame_id`, `device_sensor_link_id`.
  * Actuators: `new_device_actuator_name`, `new_device_actuator_id`, `device_actuator_kind`, `device_actuator_joint_id`, `device_actuator_coordinate_id`.
* **Muscle Fields**: `muscle_id`, `muscle_name`, `new_path_point_name`, `new_path_point_id`, `path_point_kind`, `path_point_body_id`, `path_point_frame_id`, `path_point_order`.
  * Wraps: `new_wrap_name`, `new_wrap_id`, `wrap_kind`, `wrap_body_id`, `wrap_frame_id`, `wrap_radius`, `wrap_height`.
* **Assembly Fields**: `assembly_id`, `assembly_name`, `new_attachment_name`, `new_attachment_id`, `attachment_device_id`, `attachment_interface_id`, `attachment_anatomical_site_id`.
* **Landmark Fields**: `new_landmark_name`, `new_landmark_id`, `landmark_body_id`, `landmark_frame_id`.
* **Export**: `export_path`.

## 11. Skin Reference Data

The current example workflow can create non-export reference data used to visualize skin-fitting inputs alongside the canonical project.

* **Reference Collection**: A separate collection named `"Skin Reference (non-export)"` may be created to hold non-canonical skin reference objects.
* **Exclusion from Export**: Reference objects carry a `skin_reference=True` custom property. The standard project export builder identifies and excludes these objects so the exported `Project` remains canonical.
* **Scope**: This is an example-workflow visualization aid, not a separate canonical project import format.

## 12. Authoring Conventions

To maintain a consistent and valid model, follow these conventions:

* **Naming**: Blender object names are purely for display. Always use the `melos_id` property for canonical references between entities.
* **ID Stability**: Once an entity is created, avoid changing its `melos_id` if other entities (like frames or joints) reference it.
* **Creation Order**:
    1. Create **Bodies** first.
    2. Create **Frames** and parent them to Bodies.
    3. Create **Joints** which reference the existing Frames.
* **Validation**: Regularly use the "Validate Project" button to catch orphaned frames, circular joint dependencies, or missing properties.
* **Root Link**: The first anatomical body/link created in a scene is typically automatically assigned as the `anatomical_root_link_id`, which serves as the base of the kinematic tree.

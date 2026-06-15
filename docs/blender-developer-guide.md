# melos-blender Developer Guide

This guide is for contributors changing the Blender addon, scene builders, JSON import path, or fake-bpy tests. For user-facing addon reference material, see `docs/blender-addon-guide.md`.

## Role of `melos.blender`

`melos.blender` is a visual authoring frontend over canonical `melos.core` dataclasses.

The addon should:

- create and edit tagged Blender objects,
- rebuild a `melos.core.Project` from scene state,
- import a `Project` back into tagged scene objects,
- run core validation before export,
- avoid owning canonical domain semantics that belong in `melos.core`.

Blender object names are display labels. Stable references must use custom properties such as `melos_id`.

## Package layers

```text
melos.blender
├── constants.py       Shared custom-property keys and entity-kind strings
├── addon/
│   ├── properties.py  Scene settings stored at scene.melos_blender
│   ├── operators/     Blender operators that create/tag objects or run workflows
│   ├── panels/        Sidebar UI panels that expose properties/operators
│   └── register.py    Blender class registration and Scene pointer property
├── bpy_io/
│   ├── project.py     Master scene -> Project builder
│   ├── importer.py    Project -> tagged scene object importer
│   ├── anatomical.py  Anatomical-system scene extraction
│   ├── device.py      Device-system scene extraction, including cable routes
│   ├── assembly.py    Attachment/assembly extraction
│   ├── assets.py      Asset-library extraction
│   ├── muscle.py      Muscle path/wrap extraction
│   └── transforms.py  Blender-object matrix -> core Transform conversion
└── services/          Pure-Python helpers used by addon and tests
```

Keep logic in the lowest layer that can own it:

- UI-only behavior: `addon/operators` or `addon/panels`.
- Scene custom-property translation: `bpy_io`.
- Reusable pure logic: `services`.
- Domain schema/validation: `melos.core`.

## Scene tagging contract

Every authorable MELOS entity is a Blender object with at least:

- `melos_entity_kind` (`ENTITY_KIND_KEY`): entity discriminator.
- `melos_id` (`ENTITY_ID_KEY`): stable canonical ID.
- `melos_name` (`DISPLAY_NAME_KEY`): optional display name persisted into core models.

Common entity kinds:

| Entity kind | Core target |
| --- | --- |
| `anatomical_link` | `SystemModel.links` on the anatomical system |
| `anatomical_site` | `SystemModel.sites` on the anatomical system |
| `anatomical_joint` | `SystemModel.joints` on the anatomical system |
| `anatomical_link_asset` | `AssetLibrary` + link asset references |
| `device_link` | `SystemModel.links` on the device system |
| `device_frame` | `SystemModel.sites` on the device system |
| `device_joint` | `SystemModel.joints` on the device system |
| `device_sensor` | `SystemModel.sensors` on the device system |
| `device_actuator` | `SystemModel.actuators` on the device system |
| `device_cable_route_point` | `Actuator.route` nodes grouped by actuator ID |
| `muscle_path_point` | muscle actuator route/legacy muscle path authoring |
| `muscle_wrap_geometry` | wrap geometry authoring |
| `attachment` | `SystemAssembly.connections` |
| `landmark` | anatomical `Site` with landmark metadata |

Use constants from `melos.blender.constants` rather than string literals in implementation code.

## Addon settings

`MELOSAddonSettings` is registered as `scene.melos_blender` in `addon/register.py`. Operators read input values from this object; panels expose those values in the UI.

When adding a new operator setting:

1. Add a typed property to `MELOSAddonSettings.__annotations__` in `addon/properties.py`.
2. Use enum values from core enums when a property maps to core semantics.
3. Add fields to the relevant panel.
4. Read the field from the operator and write it onto the created object as a custom property.
5. Add fake-bpy tests that instantiate settings directly; tests should not require Blender.

The active scene settings attribute is `melos_blender`, not `melos_settings`.

## Operator pattern

Operators in this package are intentionally thin:

- import `bpy` via `importlib.import_module("bpy")`,
- define an `OperatorBase` fallback when Blender is unavailable,
- read `context.scene.melos_blender`,
- allocate stable IDs with `services.ids.allocate_identifier()`,
- create an Empty with `_create_empty()`,
- write `ENTITY_KIND_KEY`, `ENTITY_ID_KEY`, `DISPLAY_NAME_KEY`, and feature-specific keys,
- call `report()` only if available.

Minimal shape:

```python
class MELOS_OT_create_example(OperatorBase):
    bl_idname = "melos.create_example"
    bl_label = "Create Example"

    def execute(self, context):
        settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
        existing_ids = _existing_entity_ids(context.scene, EXAMPLE_KIND)
        object_id = settings.new_example_id or allocate_identifier(
            settings.new_example_name,
            existing_ids,
            fallback="example",
        )
        object_ = _create_empty(context, name=settings.new_example_name)
        object_[ENTITY_KIND_KEY] = EXAMPLE_KIND
        object_[ENTITY_ID_KEY] = object_id
        object_[DISPLAY_NAME_KEY] = settings.new_example_name
        return {"FINISHED"}
```

Register the operator by adding it to the module-level `CLASSES` tuple and `__all__`; `addon/operators/__init__.py` aggregates `DEVICE_CLASSES`, `ANATOMICAL_CLASSES`, and other module class tuples.

## Panel pattern

Panels should expose settings and invoke operators only. They should not build core models directly.

Typical panel code:

```python
settings = getattr(context.scene, SCENE_SETTINGS_ATTRIBUTE)
box = layout.box()
box.label(text="Create Device Actuator")
box.prop(settings, "new_device_actuator_name")
box.prop(settings, "new_device_actuator_id")
box.operator("melos.create_device_actuator")
```

If a field is required by the builder but not exposed in the UI, tests should still construct it through fake settings. Prefer exposing all authorable references so a scene can be made valid without hand-editing custom properties.

## `bpy_io` builder contract

Builders translate tagged scene objects into core dataclasses. They should be deterministic and side-effect free.

Important entrypoints:

- `build_project_from_scene(scene) -> Project`
- `save_project_from_scene(scene, path) -> Project`
- `build_anatomical_system_from_scene(scene, settings) -> SystemModel`
- `build_device_from_scene(scene, settings) -> SystemModel`
- `build_assembly_from_scene(scene, settings) -> SystemAssembly`
- `import_project_to_scene(project, scene, settings, create_object=...) -> list[object]`

`build_project_from_scene()` reads `scene.melos_blender`, builds project metadata and simulation settings, extracts assets, always builds an anatomical system, conditionally builds a device system if device entities exist, and conditionally builds an assembly if attachment entities exist.

Builder rules:

- Filter scene objects by `ENTITY_KIND_KEY`.
- Use `.get(key, default)` for custom properties so fake objects and Blender objects work.
- Use `_required_string()` for references required by the core dataclass.
- Use `_optional_string()` for optional IDs.
- Use `transform_from_object()` for objects whose transform matters.
- Return core dataclasses; do not mutate scene objects.
- Preserve `melos_id` exactly.

## Importer contract

`bpy_io.importer.import_project_to_scene()` reconstructs tagged objects from a core `Project`.

Importer rules:

- Create one Blender object per authorable core entity.
- Write the same custom-property keys the builders read.
- Use stable IDs from the core model, not generated IDs.
- Use readable object names for humans, but do not rely on object names for references.
- Apply transforms where authoring depends on spatial placement.
- Accept an injectable `create_object` callback for tests.

Round-trip target: `Project -> importer -> build_project_from_scene/build_*_from_scene` should preserve the canonical fields for that feature.

## Cable routing in Blender

Cable routing is authored with one `device_actuator` plus ordered `device_cable_route_point` objects.

Actuator object:

- `melos_entity_kind = "device_actuator"`
- `melos_id = <actuator id>`
- `melos_device_actuator_kind = "cable"`
- optional `melos_device_actuator_joint_id`
- optional `melos_device_actuator_coordinate_id`

Route-point object:

- `melos_entity_kind = "device_cable_route_point"`
- `melos_id = <route point id>`
- `melos_cable_actuator_id = <actuator id>`
- `melos_cable_route_order = <numeric order>`
- `melos_cable_route_node_kind = "site" | "wrap"`
- `melos_cable_route_site_id = <site id>` for site nodes
- `melos_cable_route_geometry_id = <wrap geometry id>` for wrap nodes
- `melos_cable_route_side_site_id = <side site id>` when needed by backend lowering

`bpy_io.device.build_device_from_scene()` groups route points by `melos_cable_actuator_id`, sorts them by `melos_cable_route_order`, converts them to `RouteNode`, and attaches them to the matching `Actuator.route`.

`bpy_io.importer.import_project_to_scene()` emits matching route-point objects for existing `Actuator.route` entries.

## Transform extraction

`bpy_io.transforms.transform_from_object()` expects an object with either:

- `matrix_local.copy()` when local transforms are requested, or
- `matrix_world.copy()` as a fallback.

The matrix object must provide:

- `to_translation() -> tuple[float, float, float]`
- `to_quaternion() -> tuple[float, float, float, float]`

Fake-bpy tests should provide small fake matrix objects instead of importing Blender mathutils.

## Fake-bpy testing

Most addon logic should be testable without a running Blender instance.

Common fakes:

- `FakeObject(dict)`: custom-property storage plus `name`, `parent`, `children`, `matrix_local`/`matrix_world` if transforms are needed.
- `FakeScene`: `objects`, `collection`, and `melos_blender` settings.
- `FakeCollection`: `link(obj)` for importer/operator tests.
- `FakeSettings`: attributes matching `MELOSAddonSettings` fields touched by the test.
- `fake_create_object(name, collection)`: injectable importer object factory.

Test at the layer that owns the behavior:

- operator test: settings -> tagged object properties,
- builder test: tagged object properties -> core dataclass,
- importer test: core dataclass -> tagged object properties,
- round-trip test: core dataclass -> importer -> builder -> equivalent core fields.

Do not mock `melos.core` validation or dataclasses. Use real core objects.

## Adding a new authorable entity

Use this checklist when making a core feature authorable in Blender:

1. Add core dataclasses/enums/validation first.
2. Add constants for entity kind and custom-property keys in `constants.py`.
3. Add settings fields in `addon/properties.py`.
4. Add an operator that creates a tagged object and persists stable IDs.
5. Add panel UI for the settings/operator.
6. Add builder extraction in the owning `bpy_io/*.py` module.
7. Add importer emission in `bpy_io/importer.py`.
8. Add fake-bpy tests for operator, builder, importer, and round-trip behavior as appropriate.
9. Run focused tests, then relevant package tests.

If the feature has no visible spatial object, prefer one explicit Empty with custom properties over implicit scene-level lists. That keeps authoring inspectable and preserves Blender's undo/select workflows.

## Development commands

Editable install from the repository root:

```bash
python3 -m pip install -e ./packages/melos-core
python3 -m pip install -e ./packages/melos-skin
python3 -m pip install -e ./packages/melos-blender
```

Focused fake-bpy tests:

```bash
python3 -m pytest packages/melos-core/tests/test_blender_device.py \
  packages/melos-core/tests/test_blender_importer.py \
  packages/melos-core/tests/test_blender_cable.py -q
```

Build the installable addon zip:

```bash
python3 packages/melos-blender/scripts/build_blender_addon.py --output-dir dist
```

The packaged addon bundles `melos.blender`, `melos.core`, and the minimal `melos.skin` pieces needed by the current UI surface.

# MELOS Developer Guide

This guide outlines the development conventions, project structure, and contribution patterns for the MELOS project.

## Project Structure

MELOS is organized as a monorepo using PEP 420 namespace packages. There is no `melos/__init__.py` at the root. Each sub-package provides its own portion of the `melos` namespace.

```
melos/
├── packages/
│   ├── melos-core/     → melos.core (pure Python domain models)
│   ├── melos-blender/  → melos.blender (Blender addon)
│   ├── melos-sim/      → melos.sim / melos.sim.mujoco (simulation backends)
│   └── melos-skin/     → melos.skin (skin/model provider pipeline)
├── resources/          → pinned runtime asset snapshots used by examples and packaging
└── docs/               → documentation
```

Each package contains its source code under a `src/melos/{subpackage}/` directory structure, ensuring distinct namespaces while sharing the top-level `melos` name. Canonical paths always go through `packages/` and `resources/`; repository-root compatibility symlinks are no longer used.

## Development Setup

To set up a local development environment, use [uv](https://docs.astral.sh/uv/) from the repository root. Python 3.12 or higher is required.

```bash
uv sync --all-packages  # installs all workspace packages + dev tools
```

### Running Tests

Core tests live in `packages/melos-core/tests/` and cover core logic, Blender builders, MuJoCo compilation, and anatomical-system scaling. The root `pyproject.toml` defines a safe default test surface:

```bash
uv run pytest
```

Run the broad package suite before merging cross-package work:

```bash
uv run pytest packages/melos-core/tests packages/melos-sim \
  packages/melos-skin/tests packages/melos-blender/tests
```

Optional heavy integrations skip automatically unless their extras are installed.

## Focused Developer Guides

- `docs/core-developer-guide.md`: extending core dataclasses, validation, JSON I/O, and scaling.
- `docs/blender-developer-guide.md`: extending Blender scene tagging, operators, panels, bpy_io builders/importers, and fake-bpy tests.

## Coding Conventions

### Dataclass Rules
The project relies heavily on `dataclasses` for domain models.
- Use `@dataclass(slots=True, kw_only=True)` for all mutable models.
- Use `@dataclass(frozen=True, slots=True, kw_only=True)` only for small value types such as `Transform` or `Bounds`.
- Use `field(default=None)` for optional fields and `field(default_factory=list)` for collections.
- Do not perform validation in the constructor. Validation logic belongs in `melos.core.validation`.

### Enum Rules
- All enums must inherit from `StrEnum`.
- Enum values must be lowercase strings.
- Define enums in an `enums.py` module within the relevant subpackage.
- Enum values serve as the canonical serialization form.

### Identifier (ID) Rules
- IDs are defined as `TypeAlias = str` in `common/ids.py` or local `ids.py` modules.
- Valid IDs must match the regex pattern `^[A-Za-z][A-Za-z0-9_.-]*$` (start with a letter, followed by letters, digits, underscores, hyphens, or periods).
- IDs must be stable. Do not derive IDs from display names or labels at runtime.

### Type Hints and Units
- Use specific tuples for geometric types: `Vec3 = tuple[float, float, float]` and `Quat = tuple[float, float, float, float]`.
- The use of `Any` is prohibited.
- Do not use `# type: ignore` or equivalent suppressions.
- Prefer typed dataclasses and enums over generic dictionaries.
- Use SI units for all physical quantities. Include unit metadata in field definitions: `field(metadata={"unit": UNIT_CONSTANT})`.

### Import Rules
- `melos.core` is a pure Python package with zero external dependencies. It must not import from `blender` or `mujoco`.
- `melos.blender` and `melos.sim.mujoco` may import from `melos.core`.
- Within a package, use relative imports for sibling modules.
- Shared transform math that is needed across packages belongs in `melos.core.common.transforms`, not in backend-specific modules.

## Validation Patterns

Validation is decoupled from model instantiation and occurs in three distinct passes:
1. **References**: Checking for dangling IDs and broken links.
2. **Topology**: Verifying structural rules and hierarchy constraints.
3. **Transforms**: Ensuring numeric sanity and valid spatial configurations.

Each check generates a `ValidationIssue` containing a severity, error code, message, and location.
- **Error**: Prevents compilation or simulation.
- **Warning**: Indicates potential issues that may cause degraded performance.

To add validation, implement a check function in the appropriate validation module and register it in the `validate_project` function within `melos.core.validation.__init__`.

## Blender Testing Patterns

Tests involving Blender logic do not require a running Blender instance. They utilize "Fake" objects to simulate the `bpy` API.

- **FakeObject**: A dictionary subclass mimicking `bpy.types.Object`. It supports custom property access via `__getitem__`, and includes attributes for `name`, `matrix_world`, `type`, `data`, and `parent`.
- **FakeScene**: Contains an `objects` list and a `cursor` with location and matrix attributes.
- **FakeSettings**: Simulates `MELOSAddonSettings`.
- **FakeMatrix**: A 4x4 identity matrix simulation.

The standard test pattern involves creating a `FakeObject` with specific tags, passing it to a builder function, and asserting the properties of the resulting core model. For compiler tests, use JSON fixtures to generate a core model, run the compiler, and verify the MJCF output strings.

## Adding New Entity Types

To implement a new authorable entity type, follow these steps:

1. Define the canonical model in `melos.core` using dataclasses, enums, and ID aliases.
2. Implement validation logic in the core validation modules.
3. Ensure JSON serialization is handled, usually by adding defaulted dataclass fields and round-trip tests.
4. Define Blender constants such as entity-kind and property keys in `melos.blender.constants`.
5. Create or update a `bpy_io` builder to convert tagged scene objects to core models.
6. Create or update `bpy_io.importer` to convert core models back to tagged scene objects.
7. Implement Blender operators for entity creation.
8. Add panel UI elements for the operator settings.
9. Add MuJoCo compiler support in `melos-sim` if the entity has a simulation representation.
10. Write tests for every layer of the implementation.

## Test File Organization

Tests are categorized by their functional area:
- `test_smoke.py`: Basic import and environment checks.
- `test_json_roundtrip.py`: Serialization and deserialization integrity.
- `test_validation.py`: Core business rule validation.
- `test_mujoco_compiler.py`: Verification of generated MJCF XML.
- `test_system_model.py`: Canonical articulated-system model coverage.
- `test_blender_scaffold.py`: Logic for building system hierarchies from Blender.
- `test_blender_device.py`: Device-system operators and builders.
- `test_blender_muscle.py`: Muscle-specific operators and builders.
- `test_blender_assembly.py`: Assembly-related logic.
- `test_blender_landmark.py`: Landmark/site builders.
- `test_blender_importer.py`: Testing the JSON import process into Blender.
- `test_anatomical_link_transform.py`: Anatomical System body transform defaults and semantics.
- `test_scaling_skeleton.py`: Skeleton extraction and tree structure.
- `test_scaling_muscles.py`: Muscle path point and physiology scaling.
- `test_scaling_geometry.py`: Body, frame, landmark, wrap, and contact scaling.
- `test_scaling_inertials.py`: Inertial property scaling rules.
- `test_scaling_api.py`: Public `scale_model()` behavior and guard conditions.
- `test_scaling_e2e.py`: Import → scale → validate → compile coverage with the myoElbow fixture.

## Common Patterns

### Builder Pattern
Builders iterate through Blender scene objects, filtering by `entity_kind` tags. They collect relevant data from custom properties and object transforms to construct the final `melos.core` model.

### Compiler Pattern
The compiler iterates through the core model hierarchy. It builds XML elements for the MuJoCo MJCF format while maintaining a `_CompilerState` to track unique names and resource references.

### Scaling Pattern
Scaling code lives in `melos.core.scaling` and is written as pure functions over canonical `melos.core` models.

- `scale_model()` must return a new `Project` rather than mutating the input.
- `AnatomicalLink.transform` is the canonical parent-relative body placement used by both scaling and compilation.
- `link_vectors` inputs are parent-relative segment vectors keyed by joint name.
- New scaling behavior should be verified at three levels: focused unit tests, API behavior tests, and an end-to-end import → scale → compile test.

### Operator Pattern
Blender operators read configuration from addon settings, create `Empty` or mesh objects, and apply the required custom properties and tags to mark them as MELOS entities.

### Validation Pattern
Validation functions collect all discovered issues into a list and return a comprehensive `ValidationReport`. This allows the UI to display multiple errors to the user at once rather than failing on the first encounter.

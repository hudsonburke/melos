# Monorepo Structure

The repository now uses a cleaner top-level layout. Top-level compatibility symlinks have been removed; use `packages/...` and `resources/...` paths directly.

```text
melos/
├── packages/
│   ├── melos-core/
│   ├── melos-blender/
│   ├── melos-sim/
│   └── melos-skin/
├── resources/
│   └── third_party/
│       ├── myofullbody/
│       └── skin/
├── docs/
├── dist/
├── melospine/
└── myofullbody/
```

## Intent

- `packages/`
  - first-party melos packages that are developed together in this repo
- `resources/`
  - pinned runtime asset snapshots used by workflows, tests, and Blender addon packaging
- `docs/`
  - repository and architecture documentation
- `dist/`
  - generated build artifacts

## Canonical commands

Install editable packages:

```bash
pip install -e ./packages/melos-core
pip install -e ./packages/melos-skin
pip install -e ./packages/melos-blender
pip install -e ./packages/melos-sim
```

Run core tests:

```bash
pytest -q packages/melos-core/tests
```

Build the Blender addon:

```bash
python3 packages/melos-blender/scripts/build_blender_addon.py --output-dir dist
```

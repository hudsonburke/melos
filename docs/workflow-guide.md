# Workflow Guide

This document is being rewritten as part of the pivot from the legacy SOMA package to the new `melos.skin` package.

Current supported direction:
- `melos.sim.mujoco` imports MuJoCo models into canonical `melos.core` systems
- `melos.skin` provides first-party supported skin models, starting with MHR
- `melos.blender` displays and binds the skin to the canonical system-derived rig

Notes:
- The old `melos.soma` / `packages/melos-soma` workflow has been removed from the active codebase
- legacy workflow snippets referencing `melos.soma.api` or GEM/SOMA bundle generation are no longer current
- until this guide is rewritten, prefer the code in:
  - `packages/melos-sim/src/melos/sim/mujoco/adapters/`
  - `packages/melos-skin/src/melos/skin/`
  - `packages/melos-blender/src/melos/blender/services/example_workflow.py`
